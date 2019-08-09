'''Fill an Excel SABR Spreadsheet with values from a DVH file.
'''
from pathlib import Path
import xml.etree.ElementTree as ET
from sys import argv
from functools import partial

from plan_report import load_aliases
from plan_report import Report
from load_dvh_file import DvhFile
from load_data import load_items
from plan_data import Plan
from plan_eval_parameters import PlanEvalParameters
from report_gui import activate_gui


def define_reports(base_path: Path, data_path: Path):
    '''Load the SABR plan report definitions
    '''
    # TODO Add method to scan directory for report_definition and alias_definition files
    aliases_file = data_path / 'Aliases.xml'
    report_definition = data_path / 'ReportDefinitions.xml'

    alias_reference = load_aliases(aliases_file)

    report_tree = ET.parse(report_definition)
    report_root = report_tree.getroot()
    report_definitions = dict()
    for report_def in report_root.findall('Report'):
        report = Report(report_def, alias_reference, data_path)
        report_definitions[report.name] = report
    return report_definitions

def run_report(report_selection, report_param):
    '''Load plan data and generate report.
    '''
    plan_file_name = report_param.dvh_file
    report = report_selection[report_param.report_name]
    report.save_file = report_param.save_file
    test_plan = Plan('test1', DvhFile(plan_file_name))

    (match, not_matched) = report.match_elements(test_plan)
    report.update_references(match, not_matched)
    report.get_values(test_plan)
    report.build()


def main():
    '''Test
    '''
    if len(argv) > 1:
        base_path = Path(argv[1])
    else:
        base_path = Path('.').resolve()
        #base_path = Path(
        #            r'M:\Dosimetry Planning Documents\SABR Plan Evaluation')
    data_path = Path.cwd() / 'Data'
    report_selection = define_reports(base_path, data_path)

    report_param = PlanEvalParameters(\
        base_path=base_path,
        report_list=list(report_selection.keys()),
        save_file='SABR Plan Report.xls',
        report_name=' ')

    run_cmd = partial(run_report, report_selection)
    activate_gui(report_param, run_cmd)

if __name__ == '__main__':
    main()
