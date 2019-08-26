'''Fill an Excel SABR Spreadsheet with values from a DVH file.
'''
from copy import deepcopy
import xlwings as xw
from build_sabr_plan_report import run_report
from plan_data import DvhFile, Plan


def load_items(file_path):
    '''Read in data from a comma separated text file.
    The first line of the file defines the variable names.
    If a line has more elements than the number of variables then the last
    variable is assigned a list of the remaining elements.
        Parameters:
            file_path: type Path
                The path to the text file containing the comma separated values
            Returns:
                element_list: list of dictionaries
                    keys are the variable names
                    values are the values on a given row.
                    No type checking is done.
    '''
    file_contents = file_path.read_text().splitlines()
    variables = file_contents.pop(0).strip().split(',')
    elements = []
    for text_line in file_contents:
        row_values = text_line.strip().split(',')
        row_dict = {key: value
                    for (key, value) in zip(variables, row_values)
                    if value}
        if len(row_values) > len(variables):
            row_dict[variables[-1]] = row_values[len(variables)-1:]
        if row_dict:
            elements.append(row_dict)
    return elements


def select_test_data(base_path, test_files):
    '''Identify the dvh data file and the appropriate report name.
    '''
    sheet_lookup = {'EvaluationSheet 48Gy4F 60Gy5F': 'SABR 48 in 4',
                    'EvaluationSheet 60Gy 8F': 'SABR 60 in 8',
                    'EvaluationSheet 54Gy 3F': 'SABR 54 in 3'}
    original_results = base_path / test_files['Plan Report File']
    workbook = xw.Book(str(original_results))
    sheet_name = None
    for sheet_name in sheet_lookup:
        sheet = workbook.sheets[sheet_name]
        sheet.activate()
        test_value = sheet.range('G7').value
        if test_value:
            break
    if sheet_name:
        report_name = sheet_lookup[sheet_name]
    else:
        report_name = None
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
    while True:
        yield output_range
        output_range = output_range.offset(column_offset=column_increment)


def save_comparison(original_sheet, test_sheet, test_files, save_range):
    '''Save the original and test data into the comparison spreadsheet.
    '''
    original_data = original_sheet.range('O4:P60')
    save_range.value = original_data.value

    test_data = test_sheet.range('O4:P60')
    test_shift = original_data.shape[1]
    save_test = save_range.offset(column_offset=test_shift)
    save_test.value = test_data.value

    sheet_name = original_sheet.name
    original_dvh_file = test_files['DVH File']
    header_shift = save_test.shape[1]
    header_range = save_range.offset(row_offset=-1, column_offset=test_shift-2)
    header_range.value = [sheet_name, original_dvh_file, sheet_name,
                          'Test_results', 'Difference']

    dif_shift = test_data.shape[1]
    dif_range = save_test.offset(column_offset=dif_shift)
    dif_range = dif_range.resize(test_data.shape[0], 1)
    dif_function =  '=IFERROR(R[0]C[-3]-R[0]C[-1],EXACT(R[0]C[-1],R[0]C[-3]))'
    dif_range.formula = dif_function


def run_tests(data_path, output_itter,
              report_definition, config,
              report_file, test_list):
    '''iterate through the list of tests, load the data and
    generate a comparison.
    '''
    for test_files in test_list:
        dvh_file, report_name, original_sheet = \
            select_test_data(data_path, test_files)
        report = deepcopy(report_definition[report_name])
        report.save_file = report_file
        dvh_path = data_path / dvh_file
        plan = Plan('test', config, DvhFile(dvh_path))
        run_report(plan, report)

        test_sheet = xw.Book(str(report_file)).sheets[original_sheet.name]
        save_range = next(output_itter)
        save_comparison(original_sheet, test_sheet, test_files, save_range)
        save_range.sheet.book.save()
        original_sheet.book.close()
        test_sheet.book.close()
