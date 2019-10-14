'''Fill an Excel SABR Spreadsheet with values from a DVH file.
'''
from typing import Any, Dict, Tuple, List
from copy import deepcopy
from operator import attrgetter
from pathlib import Path
import xml.etree.ElementTree as ET

from plan_report import Report
from plan_report import load_default_laterality
from plan_report import load_aliases, load_laterality_table
from plan_data import DvhFile, Plan, PlanDescription, get_dvh_list

# TODO use file utilities functions for path and filename checking/completion
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


def load_report_definitions(report_file: Path,
                            report_parameters: dict)->Dict[str, Report]:
    '''Read in all report definitions contained in a given XML report file
    Arguments:
        report_file {Path} -- The full path to the Report definition .xml file.
        template_path {Path} -- The default directory containing the report
            template spreadsheets.
        alias_reference {AliasRef} -- A dictionary containing the Alias lookup.
        laterality_lookup {LateralityRef} -- A dictionary containing the
            laterality lookup.
        lat_patterns {Alias} -- Default aliases to use for setting laterality.
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


def read_report_files(report_path: Path, **parameters)->Dict[str, Report]:
    report_definitions = dict()
    for file in report_path.glob('*.xml'):
        file_iter = ET.iterparse(str(file), events=['start'])
        (event, elm) = file_iter.__next__()
        if 'ReportDefinitions' in elm.tag:
            report_dict = load_report_definitions(file, parameters)
            report_definitions.update(report_dict)
    return report_definitions


def find_plan_files(config, plan_path: Path = None)->List[PlanDescription]:
    '''Load DVH file headers for all .dvh files in a directory.
    If plan_path is not given, the default directory in the config file is used.
    Arguments:
        config {ET.Element} -- An XML element containing default paths.
        plan_path {Path} -- A directory containing .dvh files.
    Returns:
        List[PlanDescription] -- A sorted list containing descriptions of all
            .dvh files identified in plan_path.
    '''
    sort_list = (
        'patient_name.element_value',
        'course.element_value',
        'plan_name.element_value',
        'export_date.element_value'
        )
    plan_list = get_dvh_list(config, plan_path)
    if plan_list:
        plan_set = sorted(plan_list, key=attrgetter(*sort_list))
    return plan_set


def load_plan(config, plan_path, name='Plan', type='DVH',
              starting_data: Plan = None)->Plan:
    '''Load plan data from the specified file or folder.
    '''
    if type in 'DVH':
        plan = Plan(config, name, DvhFile(plan_path))
    # starting_data currently ignored
    return plan

def run_report(plan: Plan, report: Report):
    report.match_elements(plan)
    report.get_values(plan)
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


def initialize(base_path: Path,
               config_file: str)->Tuple[ET.Element, Dict[str, Any]]:
    '''Load the initial parameters and tables.
    Arguments:
        base_path {Path} -- The starting directory, where the config file is
            located.
        config_file {str} -- The name of the config file.
    Returns:
        Tuple[ET.Element, Dict[str, Report]] -- The configuration data and the
            report parameters.
    '''
    config = load_config(base_path, config_file)
    report_path = Path(
        config.findtext(r'./DefaultDirectories/ReportDefinitions'))
    template_path = Path(
        config.findtext(r'./DefaultDirectories/ReportTemplates'))
    alias_def = config.find('AliasList')
    laterality_lookup_def = config.find('LateralityTable')
    default_patterns_def = config.find('DefaultLateralityPatterns')

    report_parameters = dict(
        report_path=report_path,
        template_path=template_path,
        alias_reference=load_aliases(alias_def),
        laterality_lookup=load_laterality_table(laterality_lookup_def),
        lat_patterns=load_default_laterality(default_patterns_def))
    report_definitions = read_report_files(**report_parameters)
    return (config, report_definitions)



def main():
    '''Test
    '''
    #%% Load Config File Data
    base_path = Path.cwd()
    test_path = base_path / 'GUI\Testing'
    config_file = 'TestPlanEvaluationConfig.xml'
    (config, report_definitions) = initialize(test_path, config_file)

    #%% Load list of Plan Files
    plan_list = find_plan_files(config)

    #%% Select a Report
    report_name = 'SABR 48 in 4'
    #report = deepcopy(report_definitions[report_name])

    #%% Load Plan File
    #dvh_file_name = 'test.dvh'
    #test_plan = Plan(config, 'Test Plan', dvh_file_name)

    #%% Do match
    #report.match_elements(test_plan)
    #report.get_values(test_plan)
    #report.build()

    #run_cmd = partial(run_report, report_selection)
    #activate_gui(report_param, run_cmd)

if __name__ == '__main__':
    main()
