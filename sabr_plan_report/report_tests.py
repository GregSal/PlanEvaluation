'''Fill an Excel SABR Spreadsheet with values from a DVH file.
'''
from pathlib import Path
import pprint
from copy import deepcopy

import xlwings as xw
from build_sabr_plan_report import define_reports
from build_sabr_plan_report import run_report
from load_data import load_items
from plan_eval_parameters import PlanEvalParameters

def select_test_data(base_path, test_files):
    '''Identify the dvh data file and the appropriate report name.
    '''
    sheet_lookup = {'EvalutionSheet 48Gy4F or 60Gy5F': 'SABR 48 in 4',
                'Evalution Sheet 60Gy 8F': 'SABR 60 in 8'}
    original_results = base_path / test_files['Plan Report File']
    workbook = xw.Book(str(original_results))
    for sheet_name in sheet_lookup.keys():
        sheet = workbook.sheets[sheet_name]
        sheet.activate()
        test_value = sheet.range('G7').value
        if test_value:
            break
    report_name = sheet_lookup[sheet_name]
    dvh_file = test_files['DVH File']
    return dvh_file, report_name, sheet

def save_to_excel(file_name, sheet='output', starting_cell='A1',
                  column_increment=1):
    '''Iterator that returns an xlwings range pointing to the top cell of a
    column in the specified workbook.
    column_increment is the number of columns to skip between successive calls
    to the iterator.'''
    try:
        output_book = xw.books.open(str(file_name))
    except FileNotFoundError:
        output_book = xw.books.add()
        output_book.save(str(file_name))
    output_sheet = [s for s in output_book.sheets if sheet in s.name]
    if output_sheet:
        output_sheet = output_sheet[0]
    else:
        output_sheet = output_book.sheets.add(name=sheet)
    output_range = output_sheet.range(starting_cell)
    print('here')
    while True:
        yield output_range
        output_range = output_range.offset(column_offset=column_increment)

def save_comparison(original_sheet, test_sheet, test_files, save_range):
    '''Save the original and test data into the comparison spreadsheet.
    '''
    original_data = original_sheet.range('B6:G57')
    save_range.value = original_data.value

    test_data = test_sheet.range('G6:G57')
    test_shift = original_data.shape[1]
    save_test = save_range.offset(column_offset=test_shift)
    save_test.options(transpose=True).value = test_data.value

    sheet_name = original_sheet.name
    original_dvh_file = test_files['DVH File']
    header_range = save_range.offset(row_offset=-1, column_offset=test_shift-2)
    header_range.value = [sheet_name, original_dvh_file, 'Test_results']

    dif_range = save_test.offset(column_offset=1)
    dif_range = dif_range.resize(original_data.shape[0],1)
    dif_range.formula='=R[0]C[-1]-R[0]C[-2]'

def main():
    '''Test
    '''
    pp = pprint.PrettyPrinter(indent=4)
    base_path = Path(
        r'\\dkphysicspv1\e$\Gregs_Work\Plan Checking\SBRT DVH Checks')
    data_path = Path(r'.\Data').resolve()
    results_path = Path(
        r'M:\Dosimetry Planning Documents\SABR Plan Evaluation')
    report_file = results_path / 'Test Report.xls'
    comparison_file_name = results_path / 'Test results.xls'
    output_itter = save_to_excel(comparison_file_name, starting_cell='A2',
                                 column_increment=9)

    report_definition = define_reports(base_path, data_path)
    test_list_file = data_path / 'test data pairs.csv'
    test_list = load_items(test_list_file)

    for test_files in test_list:
        report_selection = deepcopy(report_definition)
        dvh_file, report_name, original_sheet = \
            select_test_data(base_path, test_files)

        report_param = PlanEvalParameters(\
            base_path=base_path,
            save_file=report_file,
            dvh_file=dvh_file,
            report_name=report_name)
        run_report(report_selection, report_param)

        test_book = xw.Book(str(report_file))
        test_sheet = test_book.sheets[original_sheet.name]
        save_range = next(output_itter)
        save_comparison(original_sheet, test_sheet, test_files, save_range)
        save_range.sheet.book.save()
        original_sheet.book.close()
        test_sheet.book.close()

if __name__ == '__main__':
    main()

