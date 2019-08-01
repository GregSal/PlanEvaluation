'''Fill an Excel SABR Spreadsheet with values from a DVH file.
'''
from pathlib import Path
from sys import argv
from functools import partial

from load_dvh_file import DvhFile
from load_data import load_items
from plan_report import Report
from plan_data import Plan
from plan_eval_parameters import PlanEvalParameters
from report_gui import activate_gui


def create_report(report_name, template_file, save_file, worksheet):
    '''Create a report and load it's definitions.
    '''
    report = Report(report_name, template_file, save_file, worksheet)
    report.save_file = save_file
    return report

def load_report_data(report, element_file, alias_file):
    '''load the definitions for a report.
    '''
    alias_list = load_items(alias_file)
    elements_list = load_items(element_file)
    report.define_elements(elements_list)
    report.add_aliases(alias_list)
    return report

def define_reports(base_path: Path, data_path: Path):
    '''Load the two SABR plan report definitions
    '''
    # generic report files
    template_file = data_path / 'SABR  Plan Evaluation Worksheet BLANK.xls'
    alias_file = data_path / 'Alias List.txt'
    save_file = base_path / 'SABR  Plan Evaluation Worksheet filled.xls'

    report_parameters = {
        'report_name': 'SABR 48 in 4',
        'worksheet': 'EvalutionSheet 48Gy4F or 60Gy5F',
        'template_file': template_file,
        'save_file': save_file
        }
    report_data = {
        'element_file': data_path / 'Report Reference 48 in 4.txt',
        'alias_file': alias_file
        }
    report_48_in_4 = create_report(**report_parameters)
    load_report_data(report_48_in_4, **report_data)

    report_parameters.update({'report_name': 'SABR 60 in 8',
                              'worksheet': 'Evalution Sheet 60Gy 8F'})
    report_data.update({
        'element_file': data_path / 'Report Reference 60 in 8.txt'})
    report_60_in_8 = create_report(**report_parameters)
    load_report_data(report_60_in_8, **report_data)

    report_selection = {'SABR 48 in 4': report_48_in_4,
                        'SABR 60 in 8': report_60_in_8}
    return report_selection

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
