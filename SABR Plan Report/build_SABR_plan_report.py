'''Fill an Excel SABR Spreadsheet with values from a DVH file.
'''
from pathlib import Path
from load_data import load_items
from plan_report import Report
from plan_data import Plan
from load_DVH_file import DVH_File


def main():
    '''Test
    '''
    template_file = \
        Path(r'..\Test Data\SABR  Plan Evaluation Worksheet Test Copy.xls')
    save_file = \
        Path(r'..\Test Data\SABR  Plan Evaluation Worksheet Test Save.xls')
    worksheet = 'EvalutionSheet 48Gy4F or 60Gy5F'
    report_48_in_4 = Report('SABR 48 in 4',
                            template_file, save_file, worksheet)

    element_file = Path(r"..\Test Data\Report Reference 48 in 4.txt")
    elements_list = load_items(element_file)
    report_48_in_4.define_elements(elements_list)
    #print(report_48_in_4)

    alias_file = Path(r"..\Test Data\Alias List.txt")
    alias_list = load_items(alias_file)
    report_48_in_4.add_aliases(alias_list)


    plan_file_name = Path(r"..\Test Data\DVH Test Data.dvh")
    plan_file = DVH_File(plan_file_name)
    test_plan = Plan('test1', plan_file_name)
    (plan_parameters, plan_structures) = plan_file.load_data()
    test_plan.add_plan_data(plan_parameters, plan_structures)
    print(test_plan)

    (match, not_matched) = report_48_in_4.match_elements(test_plan)
    report_48_in_4.update_references(match, not_matched)
    report_48_in_4.get_values(test_plan)
    report_48_in_4.build()

    report_60_in_8 = Report('SABR 60 in 8',
                            template_file, save_file, worksheet)
    element_file = Path(r"..\Test Data\Report Reference 60 in 8.txt")
    elements_list = load_items(element_file)
    report_60_in_8.define_elements(elements_list)


if __name__ == '__main__':
    main()
