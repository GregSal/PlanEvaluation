'''Run a prepared set of tests and evaluate the results.
'''
from pathlib import Path
from build_sabr_plan_report import load_config, load_report_definitions
from build_sabr_plan_report import run_report
from SABR_Plan_Report_Testing.report_tests import *


#%% Define Folder Paths
base_path = Path.cwd()
data_path = base_path / 'Data'
test_path = base_path / 'SABR_Plan_Report_Testing'
results_path = test_path / 'Output'
report_file = results_path / 'Test Report.xls'
comparison_file_name = results_path / 'Test results.xls'

#%% Load Config file and Report definitions
config_file = 'TestPlanEvaluationConfig.xml'
config = load_config(test_path, config_file)
report_definitions = load_report_definitions(config)



#%% partial Tests
#from copy import deepcopy
#import xlwings as xw
#from plan_data import DvhFile, Plan

#def run_tests(data_path, output_itter,
#             report_definition, config,
#             report_file, test_list):
#   '''iterate through the list of tests, load the data and
#   generate a comparison.
#   '''
#   test_files = test_list[4]
#   dvh_file, report_name, original_sheet = \
#       select_test_data(data_path, test_files)
#   report = deepcopy(report_definition[report_name])
#   report.save_file = report_file
#   dvh_path = data_path / dvh_file
#   plan = Plan('test', config, DvhFile(dvh_path))
#   (match, not_matched) = report.match_elements(plan)
#   run_report(plan, report)

#   test_sheet = xw.Book(str(report_file)).sheets[original_sheet.name]
#   save_range = next(output_itter)
#   save_comparison(original_sheet, test_sheet, test_files, save_range)
#   save_range.sheet.book.save()
#   original_sheet.book.close()
#   test_sheet.book.close()

#%% Run Tests
test_list = load_items(test_path / 'test data pairs.csv')
output_itter = save_to_excel(comparison_file_name, starting_cell='A2',
                             column_increment=9)
run_tests(test_path, output_itter,
          report_definitions, config,
          report_file, test_list)
pass