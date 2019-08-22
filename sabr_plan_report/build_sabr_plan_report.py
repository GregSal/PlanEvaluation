'''Fill an Excel SABR Spreadsheet with values from a DVH file.
'''
from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET

from plan_report import Report
from plan_report import load_default_laterality
from plan_report import load_aliases, load_laterality_table
from plan_data import DvhFile, Plan


def load_config(base_path: Path, config_file_name: str)->ET.Element:
    config_path = base_path / config_file_name
    config_tree = ET.parse(config_path)
    config = config_tree.getroot()
    return config


def read_report(report_file, **report_parameters):
    report_tree = ET.parse(report_file)
    report_root = report_tree.getroot()
    report_dict = dict()
    for report_def in report_root.findall('Report'):
        report = Report(report_def, **report_parameters)
        report_dict[report.name] = report
    return report_dict


def load_report_definitions(config: ET.Element):
    '''Load the SABR plan report definitions
    '''
    template_path = config.findtext(r'./DefaultDirectories/ReportTemplates')
    template_path=Path(template_path)
    alias_def = config.find('AliasList')
    laterality_lookup_def = config.find('LateralityTable')
    default_patterns_def = config.find('DefaultLateralityPatterns')

    report_parameters = dict(
        alias_reference=load_aliases(alias_def),
        template_path=Path(template_path),
        laterality_lookup=load_laterality_table(laterality_lookup_def),
        lat_patterns=load_default_laterality(default_patterns_def))

    report_definitions = dict()
    report_path = config.findtext(r'./DefaultDirectories/ReportDefinitions')
    # TODO Add method to scan directory for report_definition
    report_file = Path(report_path) / 'ReportDefinitions.xml'
    report_dict = read_report(report_file, **report_parameters)
    report_definitions.update(report_dict)
    return report_definitions


def run_report(plan, report):
    (match, not_matched) = report.match_elements(plan)
    report.get_values(plan)
    report.build()


def build_report(report_selection, report_name, plan_file_name,
                 save_file=None, plan_name='plan'):
    '''Load plan data and generate report.
    '''
    report = report_selection[report_name]
    if save_file:
        report.save_file = save_file
    plan = Plan(plan_name, DvhFile(plan_file_name))
    run_report(plan, report)



def main():
    '''Test
    '''
    #%% Load Config File Data
    base_path = Path.cwd()
    config_file = 'PlanEvaluationConfig.xml'
    config = load_config(base_path, config_file)

    #%% Load Report Definitions
    report_definitions = load_report_definitions(config)
    report_name = 'SABR 48 in 4'
    report = deepcopy(report_definitions[report_name])

    #%% Load Plan File
    dvh_file_name = 'test.dvh'
    test_plan = Plan('Test Plan', config, dvh_file_name)

    #%% Do match
    (match, not_matched) = report.match_elements(test_plan)
    report.get_values(test_plan)
    report.build()

    #run_cmd = partial(run_report, report_selection)
    #activate_gui(report_param, run_cmd)

if __name__ == '__main__':
    main()
