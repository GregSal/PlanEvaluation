'''Run a prepared set of tests and evaluate the results.
'''
from pathlib import Path
from build_sabr_plan_report import initialize, read_report_files
from SABR_Plan_Report_Testing.report_tests import load_items, save_to_excel
from SABR_Plan_Report_Testing.report_tests import run_tests


#%% Get plan structures
#import xlwings as xw
#structure_file = results_path / 'structures.xlsx'
#from plan_data import DvhFile, Plan

#def plan_structures(data_path, config, test_list):
#    '''Create a spreadsheet with lists of the structures in each test plan.
#    '''
#    structure_sheet = xw.Book().sheets.add('Plan Structures')
#    structure_column = structure_sheet.range('A1')
#    for test_files in test_list:
#        dvh_file = test_files['DVH File']
#        dvh_path = test_path / dvh_file
#        plan = Plan(config, 'test', DvhFile(dvh_path))
#        structures = [s.name for s in plan.data_elements['Structure'].values()]
#        name = [dvh_file]
#        structures = name + structures
#        structure_column.options(transpose=True).value = structures
#        structure_column = structure_column.offset(column_offset=1)


#%% partial Tests
## A variation of report_tests.run_tests() used to run selected tests
#from copy import deepcopy
#import xlwings as xw
#from plan_data import DvhFile, Plan
#from build_sabr_plan_report import run_report

#def run_tests(data_path, output_itter,
#             report_definition, config,
#             report_file, test_list):
#    '''run selected tests, load the data and
#    generate a comparison.
#    '''
#    def run_test(test_files):
#        dvh_file, report_name, original_sheet = \
#            select_test_data(data_path, test_files)
#        report = deepcopy(report_definition[report_name])
#        report.save_file = report_file
#        dvh_path = data_path / dvh_file
#        plan = Plan(config, 'test', DvhFile(dvh_path))
#        #(match, not_matched) = report.match_elements(plan)
#        run_report(plan, report)
#        test_sheet = xw.Book(str(report_file)).sheets[original_sheet.name]
#        save_range = next(output_itter)
#        save_comparison(original_sheet, test_sheet, test_files, save_range)
#        return (save_range, original_sheet)

#    test_files = test_list[1]
#    (save_range, original_sheet) = run_test(test_files)
#    test_files = test_list[8]
#    (save_range, original_sheet) = run_test(test_files)

#    save_range.sheet.book.save()
#    original_sheet.book.close()
#    test_sheet.book.close()

#%% Run Tests
def main():
    ''' Load test data and run selected tests
    '''
    #%% Define Folder Paths
    base_path = Path.cwd()
    test_path = base_path / 'SABR_Plan_Report_Testing'
    #data_path = base_path / 'Data'
    data_path = test_path
    results_path = test_path / 'Output'
    report_file = results_path / 'Test Report.xls'
    comparison_file_name = results_path / 'Test results.xls'

    #%% Load Config file and Report definitions
    config_file = 'TestPlanEvaluationConfig.xml'
    (config, report_parameters) = initialize(data_path, config_file)
    report_definitions = read_report_files(**report_parameters)
    
    #%% Load list of test files
    test_list = load_items(test_path / 'test data pairs.csv')

    #%% run all tests
    output_itter = save_to_excel(comparison_file_name, starting_cell='A2',
                                 column_increment=9)
    run_tests(test_path, output_itter,
              report_definitions, config,
              report_file, test_list)

if __name__ == '__main__':
    main()
