'''Report on Plan parameters based on defined Criteria'''

#%% imports etc.
from typing import Optional, Union, Any, Dict, Tuple, List, Set
from typing import NamedTuple
from pathlib import Path
import logging
import xml.etree.ElementTree as ET
import xlwings as xw


Alias = Union[List[Tuple[str, Optional[int]]],
              Set[Tuple[str, Optional[int]]]]
AliasIndex = Tuple[str, str, str]
AliasRef = Dict[AliasIndex, Alias]
LateralityIndex = Tuple[str, str, Optional[int]]
LateralityRef = Dict[LateralityIndex, str]

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


def get_laterality_exceptions(region_code_root: ET.Element)->List[str]:
    '''Load list of body region codes that appear to have a laterality,
        but do not.
    Arguments:
        region_code_root {ET.Element} -- An XML element containing a series of
            body region codes that end in "L", "R" or "B", where the letter
            does not indicate laterality. e.e "ORAL".
    Returns:
        List[str] -- a list of 4-letter body region codes which should not be
            treated as indicating laterality in the plan.
    '''
    region_code_list = list()
    for element in region_code_root.findall('BodyRegion'):
        region_code = element.attrib.get('Name')
        region_code_list.append(region_code)
    return region_code_list


#%% Config Methods
def load_config(base_path: Path, config_file_name: str)->ET.Element:
    '''Load the XML configuration file
    Arguments:
        base_path {Path} -- The directory containing the config file.
        config_file_name {str} -- The name of configuration file.
    Returns:
        ET.Element -- The root element of the XML config data
    '''
    config_path = base_path / config_file_name
    config_tree = ET.parse(config_path)
    config = config_tree.getroot()
    return config


def save_config(updated_config: ET.Element,
                base_path: Path, config_file_name: str):
    '''Saves the XML configuration file
    Arguments:
        base_path {Path} -- The directory containing the config file.
        config_file_name {str} -- The name of configuration file.
    Returns:
        ET.Element -- The root element of the XML config data
    '''
    config_path = base_path / config_file_name
    config_tree = ET.ElementTree(element=updated_config)
    config_tree.write(config_path)


