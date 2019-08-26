'''Report on Plan parameters based on defined Criteria'''

from typing import Dict, Tuple
from pathlib import Path
import logging
import xml.etree.ElementTree as ET
import xlwings as xw
from plan_data import Plan


logging.basicConfig(level=logging.WARNING)
LOGGER = logging.getLogger(__name__)


def load_alias_list(aliases):
    alias_list = list()
    for alias in aliases.findall('Alias'):
        size = alias.attrib.get('Size', None)
        if size:
            size = int(size)
        alias_value = (alias.text, size)
        alias_list.append(alias_value)
    return alias_list

def load_aliases(alias_root: ET.Element)->Dict[Tuple[str], str]:
    '''Read lists of alternate names for ReportElements from a .xml element.
    Arguments:
        aliases: {ET.Element} -- .xml element containing the alias lists.
    Returns {Dict[Tuple[str], str]}
        A dictionary for looking up Aliases for report elements.
        The key is a four element tuple:
            (ReferenceType, ReferenceName, Laterality, Size)
                ReferenceType: {str} -- The type of PlanElement.
                    Can be one of:
                        ('Plan Property', Structure', 'Reference Point')
            ReferenceName: {str} -- The primary reference name of the related
                report element.
            Laterality: {optional, str} -- The relative laterality of the
                related report element.
                    Can be one of:
                        ('Contralateral', 'Ipsilateral', 'Both', 'Left', 'Right')
                    or None, if a non-lateral related report element.
            Size: {optional, int} -- The size of the Laterality indicator
                required by the alias.
            Columns are:
            aliases:
                A list of alternate names for the report element.

'''
    alias_reference = dict()
    for element in alias_root.findall('PlanElement'):
        aliases = element.find('Aliases')
        if aliases is not None:
            ref_name = element.findtext('ReferenceName')
            ref_type = element.findtext('Type')
            laterality = element.findtext('Laterality')
            alias_list = load_alias_list(aliases)
            alias_index = (ref_type, ref_name, laterality)
            alias_reference[alias_index] = alias_list
    return alias_reference


def load_default_laterality(default_laterality_root):
    laterality_patterns = list()
    for element in default_laterality_root.findall('Pattern'):
        size = element.attrib.get('Size')
        if size:
            size = int(size)
            aliases = element.find('Aliases')
        pattern = element.text
        laterality_patterns.append((pattern, size))
    return laterality_patterns


def load_laterality_table(laterality_root: ET.Element)->Dict[Tuple[str], str]:
    laterality_lookup = dict()
    for element in laterality_root.findall('LateralityIndicator'):
        plan_lat = element.attrib.get('PlanLaterality')
        report_lat = element.attrib.get('ReportItemLaterality')
        size = element.attrib.get('Size')
        if size:
            size = int(size)
        laterality_index = (plan_lat, report_lat, size)
        laterality_lookup[laterality_index] = element.text
    return laterality_lookup


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
    def __init__(self, reference_def, alias_reference):
        '''Create the base dictionary and add all reference related parameters.
        '''
        super().__init__()
        self['reference_name'] = reference_def.findtext('Name')
        self['reference_type'] = reference_def.findtext('Type')
        self['reference_laterality'] = reference_def.findtext('Laterality')
        self['constructor'] = reference_def.findtext('Constructor')
        aliases_def = reference_def.find('Aliases')
        self['Aliases'] = self.add_aliases(aliases_def, alias_reference)
        self['plan_element'] = None

    def lookup_aliases(self, alias_reference):
        ref_name = self.get('reference_name')
        ref_type = self.get('reference_type')
        ref_lat = self.get('reference_laterality')
        alias_index = (ref_type, ref_name, ref_lat)
        aliases = alias_reference.get(alias_index, [])
        if ref_lat:
            alias_index = (ref_type, ref_name, None)
            aliases.extend(alias_reference.get(alias_index, []))
        return aliases

    def add_aliases(self, aliases_def, alias_reference):
        '''Add a list of alternative reference names.
        '''
        add_aliases = True
        if aliases_def is not None:
            join = aliases_def.attrib.get('Join','')
            if 'Replace' in join:
                add_aliases = False
            alias_list = load_alias_list(aliases_def)
        else:
            alias_list = list()
        if add_aliases and alias_reference:
            alias_list.extend(self.lookup_aliases(alias_reference))
        return set(alias_list)

    def match_laterality(self, plan_elements, plan_laterality=None,
                         lat_patterns=None, laterality_lookup=None):
        matched_element = None
        item_laterality = self.get('reference_laterality')
        if item_laterality:
            reference_name = self['reference_name']
            for (pattern, size) in lat_patterns:
                lat_index = (plan_laterality, item_laterality, size)
                lat_indicator = laterality_lookup[lat_index]
                lookup_name = pattern.format(Base=reference_name,
                                                LatIndicator=lat_indicator)
                matched_element = plan_elements.get(lookup_name)
                if matched_element:
                    break
        return matched_element

    def match_alias(self, plan_elements, plan_laterality=None,
                    lat_patterns=None, laterality_lookup=None):
        matched_element = None
        aliases = self.get('Aliases',{})
        item_laterality = self.get('reference_laterality')
        for (pattern, size) in aliases:
            if not size:
                matched_element = plan_elements.get(pattern)
            else:
                lat_index = (plan_laterality, item_laterality, size)
                lat_indicator = laterality_lookup.get(lat_index)
                if lat_indicator:
                    lookup_name = pattern.format(LatIndicator=lat_indicator)
                    matched_element = plan_elements.get(lookup_name)
                else:
                    matched_element = None
            if matched_element:
                break
        return matched_element

    def match_element(self, plan_elements, **lat_param):
        '''Find match in plan for report elements.
        '''
        matched_element = None
        reference_type = self['reference_type']
        reference_name = self['reference_name']
        # Try reference_name
        matched_element = plan_elements.get(reference_name)
        if not matched_element:
            # Try laterality
            matched_element = self.match_laterality(plan_elements, **lat_param)
            if not matched_element:
                # Try Aliases
                matched_element = self.match_alias(plan_elements, **lat_param)
        if matched_element:
            self['plan_element'] = matched_element
        return matched_element

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
        def read_item(target_def, target_item):
            item = target_def.findtext(target_item)
            if item:
                return str(item)
            return None

        super().__init__()
        self['Unit'] = read_item(target_def, 'Unit')
        self['CellAddress'] = read_item(target_def, 'CellAddress')
        self['CellFormat'] = read_item(target_def, 'CellFormat')

    def add_value(self, value, sheet):
        '''Enter the value into the spreadsheet.
        '''
        cell_address = self.get('CellAddress')
        if cell_address:
            cell_format = self.get('CellFormat')
            if cell_format:
                sheet.range(cell_address).number_format = cell_format
                if '%' in cell_format:
                    value = value/100
                    # spreadsheet expects percent values as a decimal
            sheet.range(cell_address).value = value

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

    def __init__(self, report_item, alias_reference):
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

        self.value = None
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
    pass

    def get_value(self, conversion_parameters):
        '''Get values for the Report Elements from the plan data.
        Parameters:
            plan: type Plan
            convert_units(starting_value, starting_units, target_units,
                  dose=1.0, volume=1.0):
        '''
        plan_element = self.reference['plan_element']
        if self.target:
            target_units = self.target.get('Unit')
        else:
            target_units = None
        constructor =self.reference.get('constructor','')
        if plan_element:
            conversion_parameters['target_units'] = target_units
            conversion_parameters['constructor'] = constructor
            self.value = plan_element.get_value(**conversion_parameters)
        pass

    def add_to_report(self, sheet):
        '''enter the ReportElement into the spreadsheet.
        Parameters:
            sheet: type xlwings worksheet
                The worksheet to enter the value into.
        '''
        value = self.value
        if value is not None:
            self.target.add_value(value, sheet)
    pass

    def table_output(self):
        '''Build an Target list string.
        '''
        item_dict = dict()
        item_dict['Item Name'] = self.name
        item_dict['Item Label'] = self.label
        item_dict['Item Category'] = self.category
        if self.reference:
            item_dict.update(self.reference)
        if self.target:
            item_dict.update(self.target)
        return item_dict

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
                 template_path: Path = Path.cwd(),
                 save_path: Path = Path.cwd(),
                 alias_reference=None,
                 laterality_lookup=None,
                 lat_patterns=None):
        '''Define the spreadsheet paths, worksheet name and Report Elements.
        '''
        self.name = report_def.findtext('Name')
        template_file_name = report_def.findtext(r'./FilePaths/Template/File')
        worksheet = report_def.findtext(r'./FilePaths/Template/WorkSheet')
        self.template_file = template_path / template_file_name
        self.worksheet = worksheet

        self.laterality_lookup = laterality_lookup
        self.lat_patterns = lat_patterns

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

    def match_elements(self, plan: Plan):
        '''Find match in plan for report elements.
        '''
        matched = dict()
        not_matched = dict()
        lat_param = dict(plan_laterality=plan.laterality,
                         lat_patterns=self.lat_patterns,
                         laterality_lookup=self.laterality_lookup)
        for report_item in self.report_elements.values():
            name = report_item.name
            reference = report_item.reference
            reference_type = reference['reference_type']
            plan_elements = plan.data_elements.get(reference_type)
            if plan_elements:
                matched_element = reference.match_element(plan_elements,
                                                          **lat_param)
            if matched_element:
                matched[name] = matched_element
            else:
                not_matched[name] = (None, None)
        return (matched, not_matched)

    def get_values(self, plan: Plan):
        '''Get values for the Report Elements from the plan data.
        Parameters:
            plan: type Plan
            convert_units(starting_value, starting_units, target_units,
                  dose=1.0, volume=1.0):
        '''
        conversion_parameters = dict(
            dose=plan.prescription_dose.element_value
            )
        for element in self.report_elements.values():
            element.get_value(conversion_parameters)
        pass

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

    def table_output(self):
        '''Build an Target list string.
        '''
        report_dict = dict()
        report_dict['Report Name'] = self.name
        report_dict['Template File'] = self.template_file
        report_dict['Template Worksheet'] = self.worksheet
        report_dict['Save File'] = self.save_file
        report_dict['Save Worksheet'] = self.save_worksheet
        item_list = list()
        for element in self.report_elements.values():
            item_dict = element.table_output()
            item_dict.update(report_dict)
            item_list.append(item_dict)
        return item_list

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

