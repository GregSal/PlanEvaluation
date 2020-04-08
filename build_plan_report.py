'''Fill an Excel SABR Spreadsheet with values from a DVH file.
'''


#%% imports etc.
from typing import Any, Dict, List
from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET
from pickle import dump, load

from plan_report import Report, read_report_files
from plan_report import load_default_laterality
from plan_report import load_aliases, load_laterality_table
from plan_data import DvhFile, Plan, PlanDescription, find_plan_files
from plan_data import get_default_units, get_laterality_exceptions, DvhSource


class IconPaths(dict):
    '''Match Parameters for a PlanReference.
        Report Item name, match status, plan item type, Plan Item name
    Attributes:
        match_icon {Path} -- Green Check mark
        not_matched_icon {str} -- The type of PlanElement.  Can be one of:
            ('Plan Property', Structure', 'Reference Point', 'Ratio')
        match_status: {str} -- How a plan value was obtained.  One of:
            One of Auto, Manual, Direct Entry, or None
        plan_Item: {str} -- The name of the matched element from the Plan.
    '''
    def __init__(self, icon_path):
        '''Initialize the icon paths.
        Attributes:
            icon_path {Path} -- The path to the Icon Directory
        Contains the following Icon references:
            match_icon {Path} -- Green Check mark
            not_matched_icon {Path} -- Red X
            changed_icon {Path} -- Yellow Sun
        '''
        super().__init__()
        # Icons
        self['match_icon'] = icon_path / 'Checkmark.png'
        self['not_matched_icon'] = icon_path / 'Error_Symbol.png'
        self['changed_icon'] = icon_path / 'emblem-new'

    def path(self, icon_name):
        '''Return a string path to the icon.
        Attributes:
            icon_name {str} -- The name of an icon in the dictionary
        '''
        icon_path = self.get(icon_name)
        if icon_path:
            return str(icon_path)
        return None


#%% Initialization Methods
# Question use file utilities functions for path and file name checking/completion?
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


#%% Report loading Methods
def set_report_parameters(config: ET.Element)->Dict[str, Any]:
    default_directories = config.find(r'./DefaultDirectories')
    template_path = Path(default_directories.findtext('ReportTemplates'))
    alias_def = config.find('AliasList')
    laterality_lookup_def = config.find('LateralityTable')
    default_patterns_def = config.find('DefaultLateralityPatterns')
    report_parameters = dict(
        template_path=template_path,
        alias_reference=load_aliases(alias_def),
        laterality_lookup=load_laterality_table(laterality_lookup_def),
        lat_patterns=load_default_laterality(default_patterns_def))
    return report_parameters

def update_reports(config: ET.Element,
                   report_locations: List[Path] = None,
                   pickle_file: Path = None)->Dict[str, Report]:
    '''Read in all report definitions from the XML report files
    located in the given directories.  Store the report definitions as a pickle file.
    Load the initial parameters and tables.
    Arguments:
        config {ET.Element} -- An XML element containing default paths.
        report_locations {List[Path]} -- A list of full paths to folders
            containing Report definition .xml files.  If not given, the paths
            defined in the config file are used.
        config_file {str} -- The name of the config file.
    Returns:
        Tuple[ET.Element, Dict[str, Report]] -- The configuration data and the
            report parameters.
    '''
    default_directories = config.find(r'./DefaultDirectories')
    if not report_locations:
        report_locations = list()
        report_path_element = default_directories.find('ReportDefinitions')
        for location in report_path_element.findall('Directory'):
            report_locations.append(Path(location.text).resolve())
    if not pickle_file:
        pickle_file = Path(default_directories.findtext('ReportPickleFile'))
    report_parameters = set_report_parameters(config)
    report_parameters.update({'report_locations': report_locations})
    report_definitions = read_report_files(**report_parameters)
    file = open(str(pickle_file), 'wb')
    dump(report_definitions, file)
    file.close()
    return report_definitions


def load_reports(config: ET.Element,
                 pickle_file: Path = None)->Dict[str, Report]:
    default_directories = config.find(r'./DefaultDirectories')
    if not pickle_file:
        pickle_file = Path(default_directories.findtext('ReportPickleFile'))
    file = open(str(pickle_file), 'rb')
    report_definitions = load(file)
    return report_definitions


#%% Plan loading Methods
def get_dvh(config: ET.Element, dvh_loc: DvhSource = None)->DvhFile:
    '''Identify a dvh plan file.
    Arguments:
        config {ET.Element} -- An XML element containing default paths.
        dvh_loc {DvhSource} -- A DvhFile object, the path, to a .dvh file,
            the name of a .dvh file in the default DVH directory, or a
            directory containing .dvh files. If not given,
            the default DVH directory in config will be used.
    Returns:
        DvhFile -- The requested or the default .dvh file.
    '''
    default_directories = config.find(r'./DefaultDirectories')
    if isinstance(dvh_loc, DvhFile):
        dvh_data_source = dvh_loc
    elif isinstance(dvh_loc, Path):
        if dvh_loc.is_file():
            dvh_data_source = DvhFile(dvh_loc)
        elif dvh_loc.is_dir():
            dvh_file_name = Path(default_directories.findtext('DVH_File'))
            dvh_file = dvh_loc / dvh_file_name
            dvh_data_source = DvhFile(dvh_file)
        else:
            return None
    elif isinstance(dvh_loc, str):
        dvh_dir = Path(default_directories.findtext('DVH'))
        dvh_file = dvh_dir / dvh_loc
        dvh_data_source = DvhFile(dvh_file)
    else:
        dvh_dir = Path(default_directories.findtext('DVH'))
        dvh_file_name = Path(default_directories.findtext('DVH_File'))
        dvh_file = dvh_dir / dvh_file_name
        dvh_data_source = DvhFile(dvh_file)
    return dvh_data_source


def load_plan(config, plan_path: DvhSource, name='Plan', plan_type='DVH')->Plan:
    '''Load plan data from the specified file or folder.
    Arguments:
        config {ET.Element} -- An XML element containing default paths.
        dvh_loc {DvhSource} -- A DvhFile object, the path, to a .dvh file,
            the name of a .dvh file in the default DVH directory, or a
            directory containing .dvh files. If not given,
            the default DVH directory in config will be used.
    Returns:
        Plan -- The requested or the default plan.
    '''
    default_units = get_default_units(config)
    code_exceptions_def = config.find('LateralityCodeExceptions')
    laterality_exceptions = get_laterality_exceptions(code_exceptions_def)
    if plan_type in 'DVH':
        dvh_file = get_dvh(config, plan_path)
        plan = Plan(default_units, laterality_exceptions, dvh_file, name)
    else:
        plan = None
    return plan


def load_dvh(plan_desc: PlanDescription, **plan_parameters)->Plan:
    '''Load plan data from the specified file or folder.
    Arguments:
        config {ET.Element} -- An XML element containing default paths.
        dvh_loc {DvhSource} -- A DvhFile object, the path, to a .dvh file,
            the name of a .dvh file in the default DVH directory, or a
            directory containing .dvh files. If not given,
            the default DVH directory in config will be used.
    Returns:
        Plan -- The requested or the default plan.
    '''
    plan_file = plan_desc.plan_file
    dvh_file = DvhFile(plan_file)
    plan = Plan(dvh_data=dvh_file, **plan_parameters)
    return plan


#%% Generate report
def run_report(plan: Plan, report: Report, save_file: Path = None, ):
    report.get_values(plan)
    if save_file:
        report.save_file = save_file
    report.build()


def build_report(config: ET.Element, report_definitions: Dict[str, Report],
                 report_name: str, plan_file_name: Path,
                 save_file=None, plan_name='plan'):
    '''Load plan data and generate report.
    '''
    report = deepcopy(report_definitions[report_name])
    if save_file:
        report.save_file = save_file
    plan = Plan(config, plan_name, DvhFile(plan_file_name))
    run_report(plan, report)


#%% Main
def main():
    '''Test
    '''
    # Load Config File Data
    base_path = Path.cwd()
    test_path = base_path / 'GUI\Testing'
    config_file = 'PlanEvaluationConfig.xml'
    config = load_config(base_path, config_file)
    report_definitions = load_reports(config)
    # Load list of Plan Files
    plan_list = find_plan_files(config)

    # Select a Report
    report_name = 'SABR 48 in 4'
    #report = deepcopy(report_definitions[report_name])

    # Load Plan File
    #dvh_file_name = 'test.dvh'
    #test_plan = Plan(config, 'Test Plan', dvh_file_name)

    # Do match
    #report.match_elements(test_plan)
    #report.get_values(test_plan)
    #report.build()

    #run_cmd = partial(run_report, report_selection)
    #activate_gui(report_param, run_cmd)

if __name__ == '__main__':
    main()
