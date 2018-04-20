'''Report on Plan parameters based on defined Criteria'''

from pathlib import Path
import logging
import xlwings as xw
from load_data import load_items
from plan_data import Element
from plan_data import Plan
from plan_data import PlanReference


logging.basicConfig(level=logging.WARNING)
LOGGER = logging.getLogger(__name__)


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
    def __init__(self, **parameters):
        '''Create the base dictionary and add values if supplied.
        '''
        super().__init__()
        if parameters:
            self.define(**parameters)

    def define(self, cell_address=None, cell_format='General', **parameters):
        '''Identify all target related parameters and update the target
        dictionary with them.
        Target related parameters are expected to begin with 'cell_' or
        'target_'.
        '''
        self['cell_address'] = str(cell_address)
        self['cell_format'] = str(cell_format)
        if parameters:
            target_keys = [key for key in parameters
                           if 'cell_' in key or 'target_' in key]
            for key in target_keys:
                value = parameters.pop(key)
                self[key] = str(value)
        return parameters

    def add_value(self, element_value, element_unit, sheet):
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

class ReportElement(Element):
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

    def __init__(self, name=None, category='Info', reference_name=None,
                 **element_params):
        '''Initialize the attributes unique to Report Elements.
        '''
        self.category = str(category)
        self.element_reference = PlanReference()
        self.element_target = Target()
        if not reference_name:
            reference_name = name
        remaining_params = self.define_reference(
            reference_name=reference_name,
            **element_params)
        remaining_params = self.define_target(**remaining_params)
        super().__init__(name=name, **remaining_params)

    def define_reference(self, **parameters):
        '''Provide reference data for the ReportElement.
        '''
        remaining_params = self.element_reference.define(**parameters)
        return remaining_params

    def update_reference(self, match):
        '''Update reference information resulting from matching with
        plan_data.
        '''
        self.element_reference.update_match(match)

    def add_aliases(self, list_of_aliases):
        '''Add a list of alternative reference names.
        '''
        self.element_reference.add_aliases(list_of_aliases)

    def define_target(self, **parameters):
        '''Provide target data for the ReportElement.
        '''
        remaining_params = self.element_target.define(**parameters)
        return remaining_params

    def __repr__(self):
        '''Build an Element.
        '''
        repr_str = super().__repr__()
        repr_str = repr_str.replace('Element', 'ReportElement')
        repr_str += 'Category: {}\n\n'.format(self.category)
        repr_str += self.element_reference.__repr__() + '\n\t'
        repr_str += self.element_target.__repr__() + '\n\t'
        return repr_str

    def add_to_report(self, sheet):
        '''enter the ReportElement into the spreadsheet.
        Parameters:
            sheet: type xlwings worksheet
                The worksheet to enter the value into.
        '''
        element_value = self.element_value
        if element_value is not None:
            self.element_target.add_value(element_value, self.unit, sheet)


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
        '''

    def __init__(self, name, template_file=None, save_file=None,
                 worksheet='Plan Report'):
        '''Define the spreadsheet paths, worksheet name and Report Elements.
        '''
        self.name = str(name)
        # Template File
        self.template_file = str(template_file)
        self.worksheet = str(worksheet)
        if save_file:
            self.save_file = str(save_file)
        else:
            self.save_file = Path(r'.\Report.xls')
        self.report_elements = dict()

    def define_elements(self, element_list):
        '''Define all of the Report Elements.
        Parameters:
            element_list: list of dictionaries containing ReportElement
                properties.  Properties may include:
                    ('name', 'reference_name', 'reference_type',
                    'reference_laterality', 'reference_constructor', 'unit',
                    'cell_address', cell_format')
        '''
        for element in element_list:
            element_name = element.get('name')
            if element_name:
                self.report_elements[element_name] = ReportElement(**element)

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
            reference = element.element_reference
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

    def insert_reference_aliases(self, element_name, alias_list):
        ''' Add alias list to element.
        '''
        self.report_elements[element_name].add_aliases(alias_list)

    def add_aliases(self, alias_list: list):
        '''Add a list of alias strings to the references.
        '''
        for alias_item in alias_list:
            element_list = self.select_by_reference(alias_item['name'],
                                                    alias_item['type'])
            for element in element_list:
                self.insert_reference_aliases(element, alias_item['aliases'])

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
                                        **element.element_reference)
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
