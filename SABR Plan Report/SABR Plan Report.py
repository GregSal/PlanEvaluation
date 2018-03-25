# Analyze and report on Plan parameters based on defined Criteria

from pathlib import Path
from LoadData import load_items
from Report import *
from PlanData import *




class Aliases(dict):
    '''A dictionary containing lists of alternate names for plan elements.
    Methods
        __init__
            Defines or loads dict
        __getattr__
            Override to return [key] if key is not found in the dictionary.
    '''
    pass


class Planlink(object):
    '''Defines the connection between a PlanElement and a given plan.
    Attributes:
            status: type str
                Defines the status of the link between the PlanElement and a
                plan.  Can be one of:
                    ('Possible Match', 'Confirmed Match', 'Unmatched',
                     'Missing', 'Manual')
            element_type type str
                Defines the type of plan element the PlanElement is
                linked with.
                Can be one of:
                    ('Structure', 'ReferencePoint', 'PlanParameter')
            element_name: type str
                The name of the plan element matched with the PlanElement.
    '''
    pass



def main():
    '''Test
    '''
    # Read in data from the plan file.
    plan_file = DVH_File(self.data_source)
    (plan_items, structures) = plan_file.load_data()
    self.plan_properties = plan_items
    self.structures = structures


    plan_file = Path(r"..\Test Data\DVH Test Data.dvh")
    test_plan = Plan('test1', plan_file)
    test_plan.load_plan()
    print (test_plan)


    element_file = Path(
                r"..\Test Data\ReportReference.txt"
                )
    elements_list = load_items(element_file)
    report_files = {
        'template_file': Path(
                r"..\Test Data\SABR  Plan Evaluation Worksheet Test Copy.xls"
                ),
        'save_file': Path(
                r"..\Test Data\SABR  Plan Evaluation Worksheet Test Save.xls"
                ),
        'worksheet': 'EvalutionSheet 48Gy4F or 60Gy5F'
        }

    report = Report('Test', **report_files, report_elements=elements_list)


    plan_values_file = Path(
            r"..\Test Data\ElementValues.txt"
            )
    element_values = load_items(plan_values_file)
    plan = {element['PlanElement']:
            dict([('element_value',element['element_value']),])
            for element in element_values}

    report.get_properties(plan)

    report.build()


if __name__ == '__main__':
    main()
