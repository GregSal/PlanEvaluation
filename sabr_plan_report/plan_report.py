'''Report on Plan parameters based on defined Criteria'''

from pathlib import Path
import logging
import xml.etree.ElementTree as ET
import pandas as pd
import xlwings as xw
from load_data import load_items
from plan_data import Plan


logging.basicConfig(level=logging.WARNING)
LOGGER = logging.getLogger(__name__)


def load_aliases(aliases_file: Path)->pd.DataFrame:
    '''Read lists of alternate names for ReportElements from a .xml file.
    Arguments:
        aliases_file: {Path} -- Path to the .xml file containing the alias lists.
    Returns {DataFrame}
        A DataFrame for looking up Aliases for report elements.
        The index is:
            element_type
                The type of PlanElement.  Can be one of:
                    ('Plan Property', Structure', 'Reference Point')
            name
                The name of the related report element
        Columns are:
            aliases:
                A list of alternate names for the report element.
            laterality:
                Indicates the laterality of a particular structure reference.
                Can be one of:
                    ('Contralateral', 'Ipsilateral', 'Both', 'Left', 'Right')
'''
    alias_tree = ET.parse(aliases_file)
    alias_root = alias_tree.getroot()
    element_list = list()
    for element in alias_root.findall('PlanElement'):
        if element is not None:
            element_dict = dict()
            element_dict['name'] = element.attrib.get('name')
            element_dict['reference_name'] = element.findtext('ReferenceName')
            element_dict['element_type'] = element.findtext('Type')
            laterality = element.findtext('Laterality')
            if laterality is not None:
                element_dict['Laterality'] = laterality
            aliases = element.find('Aliases')
            if aliases is not None:
                alias_list = list()
                for alias in aliases.findall('Alias'):
                    alias_list.append(alias.text)
                element_dict['aliases'] = alias_list
            element_list.append(element_dict)
    alias_reference = pd.DataFrame(element_list)
    alias_reference.set_index(['element_type', 'reference_name'],
                              inplace=True,
                              verify_integrity=True)
    alias_reference.dropna(inplace=True)
    return alias_reference


class PlanReference(dict):
    '''Contains information used to reference an individual Plan value.
    Used to connect ReportElements and Plan data.
    The dictionary may contain the following items as applicable:
        reference_name:
            The expected name of the related PlanElement.
        reference_aliases:
            A list of alternative names for the related PlanElement.
        reference_type:
            The type of PlanElement.  Can be one of:
                ('Plan Property', Structure', 'Reference Point')
        reference_laterality:
            Indicates the laterality of a particular structure reference.
            Can be one of:
                ('Contralateral', 'Ipsilateral', 'Both', 'Left', 'Right')
        reference_constructor:
            A string describing the method for extracting the required value.
            Includes:
                ('Volume', 'Minimum', 'Maximum', 'Mean',
                'V' # ['%', 'Gy', cGy],
                'D' # ['%', 'cc'])
        Methods
            __init__(self, **parameters)
            define(self, reference_name=None, reference_type='Plan Property',
               **parameters)
            update(self, match)
'''
    def __init__(self, reference_def, alias_reference: pd.DataFrame):
        '''Create the base dictionary and add all reference related parameters.
        '''
        super().__init__()
        self['reference_name'] = reference_def.findtext('Name')
        self['reference_type'] = reference_def.findtext('Type')
        self['Aliases'] = self.add_aliases(reference_def, alias_reference)
        for element in reference_def.findall(r'./*'):
            if 'Aliases' not in element.tag:
                self[element.tag] = str(element.text)

    def update_match(self, match):
        '''Update reference information resulting from matching with
        plan_data.
        Remove Laterality.
        '''
        if match:
            (reference_type, reference_name) = match
            self['reference_name'] = reference_name
            self['reference_type'] = reference_type
            self.pop('reference_laterality', None)
        else:
            self['reference_name'] = None

    def add_aliases(self, reference_def, alias_lookup):
        '''Add a list of alternative reference names.
        '''
        aliases = reference_def.find('Aliases')
        if aliases is not None:
            alias_list = list()
            for alias in aliases.findall('Alias'):
                alias_list.append(alias.text)
            return set(alias_list)
        else:
            ref_name = self['reference_name']
            ref_type = self['reference_type']
            try:
                alias_list = alias_lookup.loc[(ref_type, ref_name),'aliases']
            except KeyError:
                return None
            else:
                return set(alias_list)

    def __repr__(self):
        '''Build an Target list string.
        '''
        repr_str = 'Element Reference: \n\t'
        parameter_str = ''.join('{}: {}\n\t'.format(name, value)
                                for (name, value) in self.items())
        repr_str += parameter_str
        return repr_str


class Target(dict):
    '''Contains information used by a ReportElement to add it to the report.
            The dictionary may contain the following items as applicable:
                cell_address:  type str
                    The Excel cell address in "A1" format.
                cell_format:  type str
                    The Excel number format to be used for the cell.
                    Examples:
                        ('General', '@', '0.00', '0.00%', 'yyyy-mm-dd')
                        If not specified, 'General' is used.
    Methods
        __init__(self, **parameters)
        define(self, cell_address=None, cell_format='General', **parameters)
        '''
    def __init__(self, target_def):
        '''Create the base dictionary and add values if supplied.
        '''
        super().__init__()
        for element in target_def.findall(r'./*'):
            self[element.tag] = str(element.text)

    def add_value(self, element_value, sheet):
        '''Enter the value into the spreadsheet.
        '''
        cell_address = self.get('cell_address')
        if cell_address:
            cell_format = self.get('cell_format')
            if cell_format:
                sheet.range(cell_address).number_format = cell_format
                if '%' in cell_format:
                    element_value = element_value/100
                    # spreadsheet expects percent values as a decimal
            sheet.range(cell_address).value = element_value

    def __repr__(self):
        '''Build an Target list string.
        '''
        repr_str = 'Element Target: \n\t'
        parameter_str = ''.join('{}: {}\n\t'.format(name, value)
                                for (name, value) in self.items())
        repr_str += parameter_str
        return repr_str


class ReportElement():
    '''A base class for all ReportElement objects.
    A sub type of Element.
    Defines the source, category, and constructor.
    Attributes:
        category: type str
            Defines the subclass of the ReportElement.  Can be one of:
                ('Info', 'Property', 'Condition')
                If not specified, 'Info' is used.
        source: type Source
            Contains information used to link this ReportElement to a
            PlanElement.
        target: type dict
            Contains information used to write this ReportElement to the
            report.
            The dictionary may contain the following items as applicable:
                cell_address:  type str
                    The Excel cell address in "A1" format.
                cell_format:  type str
                    The Excel number format to be used for the cell.
                    Examples:
                        ('General', '@', '0.00', '0.00%', 'yyyy-mm-dd')
                        If not specified, 'General' is used.
    Methods
        __init__(self, cell_address, source=None, format='General',
                 category='Info', **element_parameters)
               **element_parameters)
        __repr__(self)
        define(self, source=None, format=None, category=None,
        add_to_report(self, sheet)
        Get properties
        Set status
        add_to_report
            Enter the value into the report and set the format.
        '''
    default_category = 'Info'

    def __init__(self, report_item, alias_reference: pd.DataFrame):
        '''Initialize the attributes unique to Report Elements.
        '''
        self.name = report_item.attrib.get('name')
        label = report_item.findtext('Label')
        if label is not None:
            self.label = label
        else:
            self.label = self.name

        category = report_item.findtext('Category')
        if category is not None:
            self.category = category
        else:
            self.category = self.default_category

        self.element_value = None
        reference = report_item.find('PlanReference')
        if reference is not None:
            self.reference = PlanReference(reference, alias_reference)
        else:
            self.reference = dict()
        target = report_item.find('Target')
        if target is not None:
            self.target = Target(target)
        else:
            self.target = None
        # If a reference name is not given use the report element name.
        if not self.reference['reference_name']:
            self.reference['reference_name'] = self.name

    def update_reference(self, match):
        '''Update reference information resulting from matching with
        plan_data.
        '''
        # TODO update_reference seems to be a redundant method
        self.reference.update_match(match)

    def add_to_report(self, sheet):
        '''enter the ReportElement into the spreadsheet.
        Parameters:
            sheet: type xlwings worksheet
                The worksheet to enter the value into.
        '''
        element_value = self.element_value
        if element_value is not None:
            self.target.add_value(element_value, sheet)

    def __repr__(self):
        '''Describe a Report Element.
        Add Report Element Attributes to the __repr__ definition of Element
        '''
        repr_str = '<ReportElement(name={}'.format(self.name)
        repr_str += 'Category: {}\n\n'.format(self.category)
        if self.element_value:
            repr_str += ', element_value={}'.format(self.element_value)
        repr_str += self.reference.__repr__() + '\n\t'
        repr_str += self.target.__repr__() + '\n\t'
        return repr_str


class Report():
    '''Defines a Plan Evaluation Report.
    Attributes:
        name:  type str
            The name of the report
        template_file:  type Path
            The path to an Excel file used as a template for the report.
            If not given a blank file will be used
        save_file: type Path
            The name to use for saving the Excel Report file.
        worksheet: type str
            The name of the Excel worksheet to save the report in.
            If not given 'Plan Report' is used.
        report_elements:  type dict of ReportElement
            A dictionary of all report elements to be entered as part of the report.
            The key is the ReportElement name and the value is the ReportElement
    Methods
        __init__(self, name, template_file=None, save_file=None,
                 worksheet='Plan Report')
        define(self, element_list)
        get_properties(self, plan)
        build(self)
        Evaluation
        '''

    def __init__(self, report_def: ET.Element,
                 alias_reference: pd.DataFrame = None,
                 data_path: Path = Path.cwd()):
        '''Define the spreadsheet paths, worksheet name and Report Elements.
        '''
        self.name = report_def.findtext('Name')
        template_file_name = report_def.findtext(r'./FilePaths/Template/File')
        self.template_file = data_path / template_file_name
        self.worksheet = report_def.findtext(r'./FilePaths/Template/WorkSheet')
        worksheet = report_def.findtext(r'./FilePaths/Template/WorkSheet')

        self.report_elements = dict()
        element_list = report_def.find('ReportItemList')
        for element in element_list.findall('ReportItem'):
            if element is not None:
                element_name= element.attrib.get('name')
                element_definition = ReportElement(element, alias_reference)
                self.report_elements[element_name] = element_definition

        save_path = report_def.findtext(r'./FilePaths/Save/Path')
        save_file_name = report_def.findtext(r'./FilePaths/Save/File')
        self.save_file = Path(save_path) / save_file_name
        self.save_worksheet = report_def.findtext(r'./FilePaths/Save/WorkSheet')


    def get_references(self, reference_type=''):
        '''Create a dictionary of references for all ReportElements.
            Key is ReportElement name
            Value is the ReportElement reference Dictionary.
        If reference_type is not given, all references will be returned.
        Returns:
            reference_dict:
                A dict of reference dictionaries for the requested
                PlanElements, with the key being the ReportElement name.
        '''
        reference_dict = dict()
        for element in self.report_elements.values():
            reference = element.reference
            if reference_type in reference['reference_type']:
                reference_dict[element.name] = reference
        return reference_dict

    def select_by_reference(self, reference_name, reference_type=''):
        '''return a list of report element names associated with the given
        reference name.
        If reference_type is not given, all references will be searched for
        the matching name.
        '''
        reference_dict = self.get_references(reference_type)
        element_list = [name for (name, reference) in reference_dict.items()
                        if reference_name in reference['reference_name']]
        return element_list

    def update_references(self, matched=None, not_matched=None):
        '''Update reference information for the ReportElements matched and
        not_matched.
            match:  type dictionary
                contains tuples of matching plan element and element_type.
        '''
        if matched:
            for (element_name, match_pair) in matched.items():
                report_element = self.report_elements[element_name]
                report_element.update_reference(match_pair)
        if not_matched:
            for element_name in not_matched:
                report_element = self.report_elements[element_name]
                report_element.update_reference(match=None)

    def match_elements(self, plan: Plan):
        '''Find match in plan for report elements.
        '''
        def try_alias(match_method, reference, alias_list=None):
            '''Loop through aliases to find a match
            '''
            item_match = None
            if alias_list:
                for alias in alias_list:
                    reference['reference_name'] = alias
                    item_match = match_method(**reference)
                    if item_match:
                        break
            return item_match

        def get_match_references(reference: PlanReference):
            '''Return a dictionary with the parameters needed for element
            matching.
            '''
            required_parameters = [
                'reference_type',
                'reference_name',
                'reference_laterality']
            alias_list = reference.pop('reference_aliases', None)
            match_reference = {key: value
                               for key, value in reference.items()
                               if key in required_parameters}
            return match_reference, alias_list

        # method to extract match references
        match = dict()
        not_matched = dict()
        do_match = plan.match_element
        for reference_type in plan.data_elements:
            report_references = self.get_references(reference_type)
            for (name, reference) in report_references.items():
                (match_ref, alias_list) = get_match_references(reference)
                item_match = do_match(**match_ref)
                if not item_match:
                    item_match = try_alias(do_match, match_ref, alias_list)
                if item_match:
                    match[name] = item_match
                else:
                    not_matched[name] = (None, None)
        return (match, not_matched)

    def get_values(self, plan: Plan):
        '''Get values for the Report Elements from the plan data.
        Parameters:
            plan: type Plan
        '''
        for element in self.report_elements.values():
            plan_value = plan.get_value(desired_unit=element.unit,
                                        **element.reference)
            if plan_value is not None:
                element.define(element_value=plan_value)

    def build(self):
        '''Open the spreadsheet and save the Report elements.
        '''
        # Use save_file workbook if open
        # else use template file if defined
        # else use new blank workbook
        try:
            open_worksheets = [bk.fullname for bk in xw.books]
        except AttributeError:
            open_worksheets = None
        if open_worksheets and (str(self.save_file) in open_worksheets):
            workbook = xw.Book(str(self.save_file))
        elif self.template_file:
            workbook = xw.Book(str(self.template_file))
        else:
            workbook = xw.Book('Plan Report')
        workbook.activate(steal_focus=True)

        # Find the appropriate worksheet or create a new one
        sheetnames = [sheet.name for sheet in workbook.sheets]
        if self.worksheet in sheetnames:
            spreadsheet = workbook.sheets[self.worksheet]
        else:
            spreadsheet = workbook.sheets.add(self.worksheet)
        spreadsheet.activate()

        # Add elements to the worksheet
        for element in self.report_elements.values():
            element.add_to_report(spreadsheet)
        workbook.save(str(self.save_file))

    def __repr__(self):
        '''Report description
        '''
        repr_str = '<' + str(self.name) + 'Report object>\n\t'
        repr_str += 'Template file path: {}\n\t'.format(self.template_file)
        repr_str += 'Worksheet name: {}\n\t'.format(self.worksheet)
        repr_str += 'Save file path: {}\n\t'.format(self.save_file)
        for element in self.report_elements.values():
            repr_str += element.__repr__()
        return repr_str


def main():
    '''Test
    '''
    template_file = \
        Path(r'..\Test Data\SABR  Plan Evaluation Worksheet Test Copy.xls')
    save_file = \
        Path(r'..\Test Data\SABR  Plan Evaluation Worksheet Test Save.xls')
    worksheet = 'EvalutionSheet 48Gy4F or 60Gy5F'
    report = Report('Test', template_file, save_file, worksheet)

    element_file = Path(r"..\Test Data\ReportReference.txt")
    elements_list = load_items(element_file)
    report.define_elements(elements_list)

    plan_values_file = Path(r'..\Test Data\ElementValues.txt')
    element_values = load_items(plan_values_file)
    plan = {element['PlanElement']:
            dict([('element_value', element['element_value']), ])
            for element in element_values}

    report.get_values(plan)
    report.build()


if __name__ == '__main__':
    main()
