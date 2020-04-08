'''Report on Plan parameters based on defined Criteria'''

#%% imports etc.
from typing import Optional, Union, Any, Dict, Tuple, List, Set
from typing import NamedTuple
from pathlib import Path
import logging
import xml.etree.ElementTree as ET
import xlwings as xw
from plan_data import Plan, PlanDataItem, ConversionParameters, Structure


Alias = Union[List[Tuple[str, Optional[int]]],
              Set[Tuple[str, Optional[int]]]]
AliasIndex = Tuple[str, str, str]
AliasRef = Dict[AliasIndex, Alias]
LateralityIndex = Tuple[str, str, Optional[int]]
LateralityRef = Dict[LateralityIndex, str]

MatchList = List[PlanDataItem]

logging.basicConfig(level=logging.WARNING)
LOGGER = logging.getLogger(__name__)

#%% Generic XML functions
def optional_load(xml_element: ET.Element, element_name: str,
                  default_value: str)->str:
    '''Read an optional text value contained in a sub-element of the supplied
        element.
    Arguments:
        xml_element {ET.Element} -- The top .xml element containing the desired
            element.
        element_name {str} -- The name (tag) of the element to search for.
        default_value {str} -- The text value to return if the element is not
            found.
    Returns:
        str -- the text value in the desired sub-element, or the default text
            value if the sub-element is not found.
    '''
    text_value = xml_element.findtext(element_name)
    if text_value is not None:
        return text_value
    return default_value


#%% Alias Methods
def load_alias_list(aliases: ET.Element)->Alias:
    '''Read in a list of alias patterns.
    Arguments:
        aliases {: ET.Element} -- An XML element defining a series of alternate
            names for a report reference.
    Returns:
        Alias -- A list of two-element tuples containing:
            alias_pattern: {str} -- An alternate name for the report reference.
                The pattern may contain the text: "{LatIndicator}", which
                    marks the location of a sub-string indicating the
                    laterality of the structure.
            Size: {optional, int} -- The size of the Laterality indicator.
                Required if "{LatIndicator}" is included in alias_pattern.
    '''
    alias_list = list()
    for alias in aliases.findall('Alias'):
        size = alias.attrib.get('Size', None)
        if size:
            size = int(size)
        alias_value = (alias.text, size)
        alias_list.append(alias_value)
    return alias_list


def load_aliases(alias_root: ET.Element)->AliasRef:
    '''Read lists of alternate names for ReportElements from a .xml element.
    Arguments:
        aliases: {ET.Element} -- .xml element containing the alias lists.
    Returns {AliasRef}
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
        The value is a list of two-element tuples containing:
            alias_pattern: {str} -- An alternate name for the report reference.
                The pattern may contain the text: "{LatIndicator}", which
                    marks the location of a sub-string indicating the
                    laterality of the structure.
            Size: {optional, int} -- The size of the Laterality indicator.
                Required if "{LatIndicator}" is included in alias_pattern.
     '''
    # TODO create an AliasReference class
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


def match_alias(aliases: Alias, plan_elements: List[PlanDataItem],
                **lat_param)->PlanDataItem:
    '''Try to find a matching plan element using the reference aliases.
    Arguments:
        aliases {Aliases} -- A list of An alternate name patterns for the
            report reference.
        plan_elements {List[PlanElement]} -- All imported plan elements.
        lat_param {Dict[str, Any]} --  may contain the following items:
            plan_laterality {str} -- The laterality of the plan.
                (default: {None})
            reference_laterality {str} -- The laterality of the report item.
                (default: {None})
            lat_patterns {Alias} -- A list of default Reference Name laterality
                modifiers (default: {None})
            laterality_lookup {LateralityRef} -- A dictionary for converting
                reference and plan laterality in to a laterality indicator.
                (default: {None})
    Returns:
        PlanElement -- The matching item from the plan.
    '''
    plan_laterality = lat_param['plan_laterality']
    reference_laterality = lat_param['reference_laterality']
    laterality_lookup = lat_param['laterality_lookup']
    matched_element = None
    for (pattern, size) in aliases:
        if not size:
            matched_element = plan_elements.get(pattern)
            if matched_element:
                break
            matched_element = match_laterality(pattern, plan_elements,
                                               **lat_param)
        else:
            lat_index = (plan_laterality, reference_laterality, size)
            lat_indicator = laterality_lookup.get(lat_index)
            if lat_indicator:
                lookup_name = pattern.format(LatIndicator=lat_indicator)
                matched_element = plan_elements.get(lookup_name)
            else:
                matched_element = None
        if matched_element:
            break
    return matched_element


#%% Laterality Methods
def load_default_laterality(default_laterality_root: ET.Element)->Alias:
    '''Read a list of default Reference Name laterality modifiers.
    Arguments:
        default_laterality_root: {ET.Element} -- .xml element containing the
            list of default Reference Name laterality modifiers.
    Returns {Alias}
        A list of two-element tuples containing:
            alias_pattern: {str} -- An alternate name for the report reference.
                The pattern should contain the text: "{Base}" and
                "{LatIndicator}", which mark the location of the unmodified
                reference name and the sub-string indicating the laterality of
                the structure, respectively.
            Size: {int} -- The size of the Laterality indicator.
    '''
    laterality_patterns = list()
    for element in default_laterality_root.findall('Pattern'):
        size = element.attrib.get('Size')
        if size:
            size = int(size)
        pattern = element.text
        laterality_patterns.append((pattern, size))
    return laterality_patterns


def load_laterality_table(laterality_root: ET.Element)->LateralityRef:
    '''Read in a lookup table that provides Laterality Indicators.
    Arguments:
        laterality_root {ET.Element} --  .xml element containing a series
        of Laterality Indicator definitions.
    Returns
        LateralityRef -- A dictionary for converting reference and plan
            laterality in to a laterality indicator.
        The key is a three element tuple:
            (PlanLaterality, ReportItemLaterality, Size)
            PlanLaterality: {str} -- The laterality of the plan. One of:
                ('Right', 'Left', 'Both', 'None')
            ReportItemLaterality: {str} -- The laterality of the report item. One of:
                    ('Ipsilateral', 'Contralateral', 'Proximal', 'Both')
            Size: {optional, int} -- The size of the Laterality indicator.
        The value is the laterality indicator string.
    '''
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


def match_laterality(reference_name: str,
                     plan_elements: Dict[str, PlanDataItem],
                     plan_laterality: str = None,
                     reference_laterality: str = None,
                     lat_patterns: Alias = None,
                     laterality_lookup: LateralityRef = None)->PlanDataItem:
    '''Identify the plan element that matches this reference.
    Arguments:
        reference_name: {str} -- The base name to use for matching.
        plan_elements {Dict[PlanElement]} -- All imported plan elements.
    Keyword Arguments:
        plan_laterality {str} -- The laterality of the plan.
            (default: {None})
        reference_laterality {str} -- The laterality of the report item.
            (default: {None})
        lat_patterns {Alias} -- A list of default Reference Name laterality
            modifiers (default: {None})
        laterality_lookup {LateralityRef} -- A dictionary for converting
            reference and plan laterality in to a laterality indicator.
            (default: {None})
    Returns:
        PlanElement -- The matching item from the plan.
    '''
    matched_element = None
    if reference_laterality:
        for (pattern, size) in lat_patterns:
            lat_index = (plan_laterality, reference_laterality, size)
            lat_indicator = laterality_lookup[lat_index]
            lookup_name = pattern.format(Base=reference_name,
                                         LatIndicator=lat_indicator)
            matched_element = plan_elements.get(lookup_name)
            if matched_element:
                break
    return matched_element


#%% Report classes
class ReferenceGroup(NamedTuple):
    '''Match Parameters for a PlanReference.
        Report Item name, match status, plan item type, Plan Item name
    Attributes:
        reference_name {str} -- The name of the PlanReference
        reference_type {str} -- The type of PlanElement.  Can be one of:
            ('Plan Property', Structure', 'Reference Point', 'Ratio')
        match_status: {str} -- How a plan value was obtained.  One of:
            One of Auto, Manual, Direct Entry, or None
        plan_Item: {str} -- The name of the matched element from the Plan.
    '''
    reference_index: Tuple[str]
    reference_name: str
    reference_type: str
    laterality: str = None
    match_status: str = None
    plan_Item: str = None

    def get_match_name(self)->str:
        '''Form a match name from a reference name and laterality.
        Returns:
            str -- A unique name for the reference that includes laterality.
        '''
        lat = self.laterality
        if not lat:
            lat = ''
        name = lat + self.reference_name
        return name
    match_name = property(get_match_name)


class PlanReference(dict):
    '''Contains information used to reference an individual Plan value.
    Used to connect ReportElements and Plan data.
    The dictionary may contain the following items as applicable:
        reference_name: {str} -- The expected name of the related PlanElement.
        reference_aliases: {Alias} -- A list of alternative names for the
            related PlanElement.
        reference_type: {str} -- The type of PlanElement.  Can be one of:
            ('Plan Property', Structure', 'Reference Point', 'Ratio')
        reference_laterality: {str} -- Indicates the laterality of a particular
            structure reference.  Can be one of:
                ('Ipsilateral', 'Contralateral', 'Proximal', 'Both')
        match_method: {str} -- How a plan value was obtained.  One of:
            	One of Auto, Manual, Direct Entry, None

        constructor:
            A string describing the method for extracting the required value.
            Includes:
                ('Volume', 'Min Dose', 'Max Dose', 'Mean Dose', 'Ratio',
                'V' # ['%', 'Gy', cGy],
                'D' # ['%', 'cc'])
        Aliases: {AliasRef} -- A dictionary for looking up Aliases for report
            elements.
        plan_element: {PlanElement} -- THe matched element from the Plan.
    Arguments:
        reference_def {ET.Element} -- .xml element containing information
            used to link a ReportElement to an individual Plan item and
            value.
        alias_reference {AliasRef} -- A dictionary for looking up Aliases
            for report elements.
    Methods
        lookup_aliases(alias_reference: AliasRef)->Alias
            Lookup possible aliases for the reference name.
        add_aliases(aliases_def: ET.Element, alias_reference: AliasRef)->Alias:
            Get all appropriate alias strings for a reference.
        match_element(plan_elements: List[PlanElement], **lat_param)->PlanElement:
            Try to find a matching plan element.
    '''
    def __init__(self, reference_def: ET.Element, alias_reference: AliasRef):
        '''Create the base dictionary and add all reference related parameters.
        Arguments:
            reference_def {ET.Element} -- .xml element containing information
                used to link a ReportElement to an individual Plan item and
                value.
            alias_reference {AliasRef} -- A dictionary for looking up Aliases
                for report elements.
        '''
        super().__init__()
        self['reference_name'] = reference_def.findtext('Name')
        self['reference_type'] = reference_def.findtext('Type')
        self['reference_laterality'] = reference_def.findtext('Laterality')
        aliases_def = reference_def.find('Aliases')
        self['Aliases'] = self.add_aliases(aliases_def, alias_reference)
        self['plan_element'] = None
        self['match_method'] = None

    def get_plan_item_name(self)->str:
        '''Return the name of the matched PlanElement, or None if no match.
        '''
        plan_item = self.get('plan_element')
        if isinstance(plan_item, (PlanDataItem, Structure)):
            return self['plan_element'].name
        return None

    matched_name = property(get_plan_item_name)

    @property
    def ref_index(self):
        ref_name = self.get('reference_name')
        ref_type = self.get('reference_type')
        ref_lat = self.get('reference_laterality')
        indx = (ref_type, ref_name, ref_lat)
        return indx

    def lookup_aliases(self, alias_reference: AliasRef)->Alias:
        '''Lookup possible aliases for the reference name.
        Arguments:
            alias_reference {AliasRef} -- A dictionary for looking up Aliases
                for report elements.
        Returns:
            Alias --  A list of two-element tuples containing: alias_pattern
                and optionally size.
        '''
        ref_name = self.get('reference_name')
        ref_type = self.get('reference_type')
        ref_lat = self.get('reference_laterality')
        alias_index = (ref_type, ref_name, ref_lat)
        aliases = alias_reference.get(alias_index, [])
        if ref_lat:
            alias_index = (ref_type, ref_name, None)
            aliases.extend(alias_reference.get(alias_index, []))
        return aliases

    def add_aliases(self, aliases_def: ET.Element,
                    alias_reference: AliasRef)->Alias:
        '''Get all appropriate alias strings for a reference.
        Arguments:
            aliases_def {ET.Element} -- xml element containing alternate
                structure names for a reference.
            alias_reference {AliasRef} -- A dictionary for looking up Aliases
                for report elements.
        Returns:
            Alias -- A set of all relevant Aliases
        '''
        add_aliases = True
        if aliases_def is not None:
            join = aliases_def.attrib.get('Join', '')
            if 'Replace' in join:
                add_aliases = False
            alias_list = load_alias_list(aliases_def)
        else:
            alias_list = list()
        if add_aliases and alias_reference:
            alias_list.extend(self.lookup_aliases(alias_reference))
        return set(alias_list)

    def match_element(self, plan_elements: List[PlanDataItem],
                      **lat_param)->PlanDataItem:
        '''Try to find a matching plan element.
        Arguments:
            plan_elements {List[PlanElement]} -- All imported plan elements.
        lat_param {Dict[str, Any]} --  may contain the following items:
            plan_laterality {str} -- The laterality of the plan.
                (default: {None})
            lat_patterns {Alias} -- A list of default Reference Name laterality
                modifiers (default: {None})
            laterality_lookup {LateralityRef} -- A dictionary for converting
                reference and plan laterality in to a laterality indicator.
                (default: {None})
        Returns:
            PlanElement -- The matching item from the plan.
        '''
        matched_element = None
        reference_name = self['reference_name']
        # Try reference_name
        matched_element = plan_elements.get(reference_name)
        if not matched_element:
            # Try laterality
            lat_param['reference_laterality'] = self.get('reference_laterality')
            matched_element = match_laterality(reference_name, plan_elements,
                                               **lat_param)
            if not matched_element:
                # Try Aliases
                aliases = self.get('Aliases', {})
                matched_element = match_alias(aliases, plan_elements,
                                              **lat_param)
        if matched_element:
            self['plan_element'] = matched_element
            self['match_method'] = 'Auto'
        return matched_element

    def reference_group(self)->ReferenceGroup:
        '''Return a tuple of match parameters
        Report Item name, match status, plan item type, Plan Item name
        '''
        return ReferenceGroup(self.ref_index,
                              self['reference_name'],
                              self['reference_type'],
                              self['reference_laterality'],
                              self['match_method'],
                              self.matched_name)

    match = property(reference_group)

    def update_ref(self, new_ref: ReferenceGroup, plan: Plan)->bool:
        updated = False
        self['match_method'] = new_ref.match_status
        if not new_ref.match_status:
            self['plan_element'] = None
            updated = True
        elif new_ref.match_status is 'Direct Entry':
            self['plan_element'] = new_ref.plan_Item
            updated = True
        elif new_ref.match_status is 'Manual':
            matched_element = plan.get_data_element(new_ref.reference_type,
                                                    new_ref.plan_Item)
            self['plan_element'] = matched_element
            updated = True
        return updated

    def __repr__(self)->str:
        '''Build an Target list string.
        Returns:
            str -- A string summarizing the PlanReference instance.
        '''
        repr_str = 'Element Reference: \n\t'
        parameter_str = '\n\t'.join('{}: {}'.format(name, value)
                                    for (name, value) in self.items())
        repr_str += parameter_str + '\n'
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
    def __init__(self, target_def: ET.Element):
        '''Create the base dictionary and set the supplied target values.
        Arguments:
            target_def {ET.Element} -- .xml element containing information
                used to link a ReportElement to an Excel spreadsheet cell.
        '''
        def read_item(target_def: ET.Element, target_item: str)->str:
            '''Search for a target_item element within target_def.
                Return the resulting text.
            Arguments:
                target_def {ET.Element} -- .xml Target element
                target_item {str} -- the "tag" of an element.
            Returns:
                str -- The text associated with target_item element.
                    Returns None if target_item is not found.
            '''
            item = target_def.findtext(target_item)
            if item:
                return str(item)
            return None

        super().__init__()
        self['Unit'] = read_item(target_def, 'Unit')
        self['CellAddress'] = read_item(target_def, 'CellAddress')
        self['CellFormat'] = read_item(target_def, 'CellFormat')

    def add_value(self, value: Any, sheet: xw.Sheet):
        '''Enter the value into the spreadsheet.
        Arguments:
            value {Any} -- The value to be placed in the target cell.
            sheet {xw.Sheet} -- The Excel worksheet containing the target cell.
        '''
        cell_address = self.get('CellAddress')
        if cell_address:
            cell_format = self.get('CellFormat')
            if cell_format:
                # Set the cell format
                sheet.range(cell_address).number_format = cell_format
                if '%' in cell_format:
                    value = value/100
                    # spreadsheet expects percent values as a decimal
            # Set the cell Value
            sheet.range(cell_address).value = value

    def __repr__(self)->str:
        '''Build an Target list string.
        Returns:
            str -- A string summarizing the Target instance.
        '''
        repr_str = 'Element Target: \n\t'
        parameter_str = '\n\t'.join('{}: {}'.format(name, value)
                                    for (name, value) in self.items())
        repr_str += parameter_str +'\n'
        return repr_str


class ReportElement():
    '''A base class for all ReportElement objects.
    Defines the source, category, and constructor.
    Arguments:
        report_item {ET.Element} -- .xml element containing parameters
            defining a report item.
        alias_reference {AliasRef} -- A dictionary for looking up Aliases
            for report elements.
    Attributes:
        name {str} --  The name of the report item. Required.
        label {str} -- A descriptive label for the item. If label is not
            supplied in the report item definition, then label = name.
            In the future may be used as text in the excel report for
                optional items.
        category {str} -- Defines the subclass of the ReportElement. One of:
                ('Info', 'Property', 'Condition')
                If not specified, 'Info' is used. Currently not used.
        value {Any} -- The item value extracted from the plan data. Initialized
            as None. If value is a number the units are those specified in the
            target attribute.
        reference {PlanReference} --  Contains information used to link this
            report item to a plan value.  All report item definitions must
            contain a plan reference definition.
        target {Optional, Target} -- Contains information used to add the item
            value to the report.  Omitting the target attribute will cause the
            value to be obtained from the plan data but not directly displayed
            in the report. The item value can be accessed by other report items
            for calculations or validity checks.
    Methods
        get_value(conversion_parameters: ConversionParameters)
            Get the matching value from the plan data and perform any necessary
            unit conversions.
        add_to_report(sheet: xw.Sheet)
            Enter the report item value into the spreadsheet.
        table_output(add_reference=False, add_target=False)->Dict[str, Any]
            Build a dictionary containing the key attributes defining the
            ReportElement.
        __repr__(self)->str
            Provide a formatted string describing this ReportElement.
        '''
    default_category = 'Info'

    def __init__(self, report_item: ET.Element):
        '''Initialize the Report Item attributes.
        Arguments:
            report_item {ET.Element} -- .xml element containing parameters
                defining a report item.
            alias_reference {AliasRef} -- A dictionary for looking up Aliases
                for report elements.
        '''
        self.name = report_item.attrib.get('name')
        self.label = optional_load(report_item, 'Label', self.name)
        self.category = optional_load(report_item, 'Category',
                                      self.default_category)
        self.constructor = optional_load(report_item, 'Constructor', '')
        self.value = None
        self.reference = None
        target = report_item.find('Target')
        if target is not None:
            self.target = Target(target)
        else:
            self.target = None

    def get_value(self, reference: PlanReference,
                  conversion: ConversionParameters):
        '''Get the matching value from the plan data.  Perform any necessary
            unit conversions.
        Arguments:
            conversion {ConversionParameters} -- A dictionary containing the
                data used to perform any necessary unit conversion.  Starts
                with only one item:
                    'dose' {float} -- the plan prescription dose
                Additional items are added before passing through to the
                PlanElement.get_value method.
        '''
        plan_element = reference['plan_element']
        if plan_element:
            target_units = self.target.get('Unit')
            conversion['target_units'] = target_units
            conversion['constructor'] = self.constructor
            self.value = plan_element.get_value(**conversion)
        return self.value

    def add_to_report(self, sheet: xw.Sheet):
        '''Enter the report item value into the spreadsheet.
        Arguments:
            sheet {xw.Sheet} -- The Excel worksheet where the value is to be
                placed.
        '''
        value = self.value
        if value is not None:
            self.target.add_value(value, sheet)
        return value

    def table_output(self, references: Dict[str, PlanReference],
                     add_target=False)->Dict[str, Any]:
        '''Build a dictionary containing the key attributes defining the
        ReportElement.  Used to generate the representative string and for
            testing purposes.
        Arguments:
            add_reference {bool} -- Include the reference instance data in the
                dictionary. Default is False
            add_target {bool} -- Include the target instance data in the
                dictionary. Default is False
        Returns:
            Dict[str, Any] -- Dictionary containing the key attributes
                defining the ReportElement.
        '''
        item_dict = dict()
        item_dict['ItemName'] = self.name
        item_dict['ItemLabel'] = self.label
        item_dict['ItemCategory'] = self.category
        item_dict['ItemValue'] = self.value
        reference = references.get(self.reference)
        if reference:
            item_dict['Reference'] = reference
        if add_target and self.target:
            item_dict.update(self.target)
        return item_dict

    def _to_str(self, references: Dict[str, PlanReference],
                 add_references: bool, add_target: bool)->str:
        '''Provide a formatted string describing this ReportElement.
        Returns:
            str -- A formatted string describing this ReportElement.
        '''
        item_dict = self.table_output(references, add_target)
        repr_str = '\nReportElement(\n'
        repr_str = '\tName={ItemName}\n'
        repr_str += '\tLabel: {ItemLabel}\n'
        repr_str += '\tCategory: {ItemCategory}\n'
        formatted_string = repr_str.format(**item_dict)
        if self.value:
            repr_str += '\tValue = {ItemValue}\n'
        if add_references:
            reference = references.get(self.reference)
            ref_str = reference.__repr__()
            repr_str += '\n'.join('\t' + line for line in ref_str.splitlines())
            repr_str += '\n'
        if add_target and self.target:
            tgt_str = self.target.__repr__()
            repr_str += '\n'.join('\t' + line for line in tgt_str.splitlines())
            repr_str += '\n'
        return formatted_string


class Report():
    '''Defines a Plan Evaluation Report.
    Arguments:
        report_def {ET.Element} -- The top element of a report definition
            from an XML file.
    Keyword Arguments:
        template_path {Path} -- The directory containing the excel template
            used by the report. (default: {Path.cwd()})
        save_path {Path} -- The path, including file name, where the filled
            template is to be saved. (default: {Path.cwd()})
        alias_reference {AliasRef} -- A dictionary for looking up Aliases
            for report elements. (default: {None})
        laterality_lookup {LateralityRef} -- A dictionary for converting
            reference and plan laterality in to a laterality indicator.
            (default: {None})
        lat_patterns {List[Alias]} -- A list of default Reference Name
            laterality modifiers (default: {None})
    Attributes:
        name {str} -- The name of the report
        template_file {Path} -- The directory containing the excel template
            used by the report. If not given a blank file will be used.
        save_file {Path} -- The path, including file name, where the filled
            template is to be saved.
        worksheet {str} -- The name of the Excel worksheet containing the
            report template. If not given 'Plan Report' is used.
        laterality_lookup {LateralityRef} -- A dictionary for converting
            reference and plan laterality in to a laterality indicator.
        lat_patterns {List[Alias]} -- A list of default Reference Name
            laterality modifiers.
        report_elements {Dict[str, ReportElement]} -- A dictionary of all
            report elements to be entered as part of the report.
            The key is the element item name and the value is a ReportElement.
    Methods
        match_elements(self, plan: Plan)->Tuple[MatchList, MatchList]
            Find match in plan for report elements.
        get_values(self, plan: Plan)
            Get values for the Report Elements from the plan data.
        build(self)->xw.Sheet
            Open the spreadsheet and save the Report elements.
        table_output(self, add_items=True, flat_table=False,
                     add_reference=True, add_target=True)->Dict[str, Any]
            Build a dictionary summarizing the report definition.
        __repr__(self, add_items=True)->str
            Provide a formatted string describing this Report.
    '''
    def __init__(self, report_def: ET.Element,
                 template_path: Path = Path.cwd(),
                 save_path: Path = Path.cwd(), # FIXME this is not a full file path.
                 alias_reference: AliasRef = None,
                 laterality_lookup: AliasRef = None,
                 lat_patterns: List[Alias] = None):
        '''Load and generate a report definition.
        Arguments:
            report_def {ET.Element} -- The top element of a report definition
                from an XML file.
        Keyword Arguments:
            template_path {Path} -- The directory containing the excel template
                used by the report. (default: {Path.cwd()})
            save_path {Path} -- The path, including file name, where the filled
                template is to be saved. (default: {Path.cwd()})
            alias_reference {AliasRef} -- A dictionary for looking up Aliases
                for report elements. (default: {None})
            laterality_lookup {LateralityRef} -- A dictionary for converting
                reference and plan laterality in to a laterality indicator.
                (default: {None})
            lat_patterns {List[Alias]} -- A list of default Reference Name
                laterality modifiers (default: {None})
        '''
        self.name = report_def.findtext('Name')
        self.description = report_def.findtext('Description').strip()
        template_file_name = report_def.findtext(r'./FilePaths/Template/File')
        worksheet = report_def.findtext(r'./FilePaths/Template/WorkSheet')
        self.template_file = template_path / template_file_name
        self.worksheet = worksheet
        self.laterality_lookup = laterality_lookup
        self.lat_patterns = lat_patterns

        self.references = dict()
        self.report_elements = dict()
        element_list = report_def.find('ReportItemList')
        for element in element_list.findall('ReportItem'):
            if element is not None:
                element_name = element.attrib.get('name')
                element_definition = ReportElement(element)
                reference = element.find('PlanReference')
                element_name = element_definition.name
                reference_index = self.add_reference(reference, alias_reference,
                                                    element_name)
                element_definition.reference = reference_index
                self.report_elements[element_name] = element_definition

        save_path = report_def.findtext(r'./FilePaths/Save/Path')
        save_file_name = report_def.findtext(r'./FilePaths/Save/File')
        self.save_file = Path(save_path) / save_file_name
        self.save_worksheet = report_def.findtext(r'./FilePaths/Save/WorkSheet')

    def add_reference(self, reference_def, alias_reference, element_name):
        '''build reference lookup'
        '''
        if reference_def is None:
            return None
        # TODO Check whether reference points to another Report Element
        # TODO Ratio etc. should not generate new references, but should point to existing report items.
        reference = PlanReference(reference_def, alias_reference)
        # If a reference name is not given use the report element name.
        reference_name = reference['reference_name']
        if not reference_name:
            reference['reference_name'] = element_name
            reference_name = element_name
        self.references[reference.ref_index] = reference
        return reference.ref_index

    def match_elements(self, plan: Plan)->Tuple[MatchList, MatchList]:
        '''Find match in plan for report elements.
        Arguments:
            plan {Plan} -- The plan data to match
        Returns:
            Tuple[MatchList, MatchList] -- Dictionaries of matched and
                unmatched report items. The key is the ReportElement name.
                For matched, the value is the matching plan item.
                For unmatched the value is None.
        '''
        matched = list()
        not_matched = list()
        lat_param = dict(plan_laterality=plan.laterality,
                         lat_patterns=self.lat_patterns,
                         laterality_lookup=self.laterality_lookup)
        for report_item in self.report_elements.values():
            reference_name = report_item.reference
            reference = self.references.get(reference_name)
            if reference:
                reference_type = reference['reference_type']
                plan_elements = plan.data_elements.get(reference_type)
            else:
                plan_elements = None
            if plan_elements:
                matched_element = reference.match_element(plan_elements,
                                                          **lat_param)
            if matched_element:
                matched.append(matched_element)
            else:
                not_matched.append(matched_element)
        return (matched, not_matched)

    def get_matches(self)->Dict[str, ReferenceGroup]:
        '''return a dictionary of reference matches
        '''
        match_data = {name: ref.match for name, ref in self.references.items()}
        return match_data

    def update_ref(self, new_ref: ReferenceGroup, plan: Plan)->bool:
        updated = False
        reference = self.references[new_ref.reference_index]
        reference['match_method'] = new_ref.match_status
        if not new_ref.match_status:
            reference['plan_element'] = None
            updated = True
        elif new_ref.match_status in 'Direct Entry':
            reference['plan_element'] = new_ref.plan_Item
            updated = True
        elif new_ref.match_status in 'Manual':
            matched_element = plan.get_data_element(new_ref.reference_type,
                                                    new_ref.plan_Item)
            reference['plan_element'] = matched_element
            updated = True
        return updated

    def get_values(self, plan: Plan):
        '''Get values for the Report Elements from the plan data.
        Arguments:
            plan {Plan} -- The plan data to obtain the values from.
        '''
        conversion_parameters = dict(
            dose=plan.prescription_dose.element_value
            )
        for element in self.report_elements.values():
            reference_name = element.reference
            reference = self.references.get(reference_name)
            if reference and reference['match_method']:
                if 'Direct Entry' in reference['match_method']:
                    element.value = reference['plan_element']
                else:
                    element.get_value(reference, conversion_parameters)
        return None

    def build(self)->xw.Sheet:
        '''Open the spreadsheet and save the Report elements.
        Returns:
            xw.Sheet -- The excel worksheet containing the completed report.
        '''
        # Use save_file workbook if open
        try:
            workbook = xw.Book(self.save_file)
        except FileNotFoundError:
            if self.template_file:
                workbook = xw.Book(str(self.template_file))
            # else use new blank workbook
            else:
                workbook = xw.Book('Plan Report')
        workbook.activate(steal_focus=True)
        # Ensure that not overwriting template file
        workbook.save(str(self.save_file))
        # Find the appropriate worksheet or create a new one
        sheetnames = [sheet.name for sheet in workbook.sheets]
        if self.worksheet in sheetnames:
            spreadsheet = workbook.sheets[self.worksheet]
        else:
            spreadsheet = workbook.sheets.add(self.worksheet)
        spreadsheet.activate()

        # Add elements to the worksheet
        for element in self.report_elements.values():
            if element.target is not None:
                element.add_to_report(spreadsheet)

        return spreadsheet

    @staticmethod
    def save(spreadsheet: xw.Sheet, file_name: Path = None, close=True):
        '''Save the report.
        '''
        exel_app = spreadsheet.api
        workbook = spreadsheet.book
        workbook.save(str(file_name))
        if close:
            workbook.close()
            exel_app.quit()

    def table_output(self, add_items=True, flat_table=False,
                     add_reference=True, add_target=True)->Dict[str, Any]:
        '''Build a dictionary summarizing the report definition.
        Arguments:
            add_items {bool} -- Include a list of report items in the
                dictionary.  Default is True
            flat_table {bool} -- Add the base report data to each report
                element dictionary.  This is useful for generating a
                spreadsheet summary. Ignored if add_items is False.
                Default is False
            add_reference {bool} -- Include the reference instance data in each
                dictionary. Ignored if add_items is False. Default is True
            add_target {bool} -- Include the target instance data in the
                dictionary. Ignored if add_items is False. Default is True.
        Returns:
            Dict[str, Any] -- A dictionary summarizing the report definition.
                If add_items is False, the dictionary only contains the
                    Report-level attributes.
                If add_items is True and flat_table is False, the dictionary
                    contains an additional item: 'ReportItems' with a list of
                    dictionaries, each containing the attributes of a
                    ReportElement.
                If add_items is True and flat_table is True, the dictionary
                    contains a single item with the key being the report name.
                    The value is : 'ReportItems' with a list of dictionaries
                    for each of the ReportElement attributes which also
                    contains the Report-level attributes.
        '''
        report_dict = dict(
            ReportName=self.name,
            TemplateFile=str(self.template_file),
            TemplateWorksheet=self.worksheet,
            SaveFile=str(self.save_file),
            SaveWorksheet=self.save_worksheet
            )
        if add_reference:
            references = self.references
        else:
            references = dict()
        if add_items:
            item_list = list()
            for element in self.report_elements.values():
                item_dict = element.table_output(references, add_target)
                if flat_table:
                    item_dict.update(report_dict)
                item_list.append(item_dict)
            if flat_table:
                table = dict()
                table[self.name] = item_list
            else:
                table = report_dict
                table['ReportItems'] = item_list
        else:
            table = report_dict
        return table

    def __repr__(self, add_references=True, add_target=True)->str:
        '''Provide a formatted string describing this Report.
        Keyword Arguments:
            add_items {bool} -- Include a list of report items in the
                string.  Default is True
        Returns:
            str -- A formatted string describing this Report.
        '''
        # Add the Report attributes
        report_data = self.table_output(add_items=False)
        repr_str = 'Report:\t{ReportName}\n'
        repr_str += '\tTemplate: {TemplateFile}[{TemplateWorksheet}]\n'
        repr_str += '\tSaveAs: {SaveFile}[{SaveWorksheet}]\n'
        repr_str = repr_str.format(**report_data)
        # Add strings for each report item
        repr_str += '\n'
        for element in self.report_elements.values():
            e_str = element._to_str(self.references, add_references, add_target)
            repr_str += '\n'.join('\t' + line for line in e_str.splitlines())
        repr_str += '\n'
        return repr_str


def load_report_definitions(report_file: Path,
                            report_parameters: dict)->Dict[str, Report]:
    '''Read in all report definitions contained in a given XML report file
    Arguments:
        report_file {Path} -- The full path to the Report .xml file.
        report_parameters {dict} -- parameters used to define reports.
            See the Report class definition for details.
    Returns:
        Dict[str, Report] -- A dictionary of report definitions, the key is
            the name of the report.
    '''
    report_tree = ET.parse(report_file)
    report_root = report_tree.getroot()
    report_dict = dict()
    for report_def in report_root.findall('Report'):
        report = Report(report_def, **report_parameters)
        report_dict[report.name] = report
    return report_dict


def read_report_files(report_locations: List[Path],
                      **parameters)->Dict[str, Report]:
    '''Read in all report definitions contained in the XML report files
    located in the given directories.
    Arguments:
        report_locations {List[Path]} -- A list of full paths to folders
            containing Report definition .xml files.
        report_parameters {dict} -- parameters used to define reports.
            See the Report class definition for details.
    Returns:
        Dict[str, Report] -- A dictionary of report definitions, the key is
            the name of the report.
    '''


    report_definitions = dict()
    for report_path in report_locations:
        for file in report_path.glob('*.xml'):
            file_iter = ET.iterparse(str(file), events=['start'])
            (event, elm) = file_iter.__next__()
            if 'ReportDefinitions' in elm.tag:
                report_dict = load_report_definitions(file, parameters)
                report_definitions.update(report_dict)
    return report_definitions


#%% Match History class and Methods
class MatchHistoryItem(NamedTuple):
    '''Record of a change made to a reference match.
    Attributes:
        old_value {ReferenceGroup} -- The value before the change
        new_value {ReferenceGroup} -- The value after the change
    '''
    old_value: ReferenceGroup
    new_value: ReferenceGroup = None


class MatchHistory(list):
    '''A record of the changes made to the reference matching.
    Attributes:
        reference_name {str} -- The name of the PlanReference
    '''
    def __init__(self):
        '''Create an empty list
        '''
        super().__init__()

    def add(self, old_value: ReferenceGroup, new_value: ReferenceGroup = None):
        '''Record a new match change.
        Arguments:
            old_value {ReferenceGroup} -- The value before the change
            new_value {ReferenceGroup} -- The value after the change
        '''
        self.append(MatchHistoryItem(old_value, new_value))

    def changed(self)->List[ReferenceGroup]:
        change_list = list()
        for hist_item in self:
            if hist_item.new_value:
                change_list.append(hist_item.new_value)
        return change_list

    def undo_last_change(self)->MatchHistoryItem:
        last_change = self.pop()
        return last_change

def rerun_matching(report: Report, plan: Plan, matches: MatchHistory)->Report:
    '''Re-run the match with updated plan data and then apply stored manual
        matching and entries.
    '''
    report.match_elements(plan)
    for change_match in matches.changed():
        report.update_ref(change_match, plan)
    return report


def undo_match(report: Report, plan: Plan, change: MatchHistoryItem)->Report:
    report.update_ref(change.old_value, plan)
    return report

def reset_matching(report: Report, plan: Plan, matches: MatchHistory)->Report:
    '''Re-run the match with updated plan data and then apply stored manual
        matching and entries.
    '''
    report.match_elements(plan)
    for change_match in matches.changed():
        report.update_ref(change_match, plan)
    matches = MatchHistory()
    return report, matches
