from pathlib import Path
from copy import deepcopy
import xml.etree.ElementTree as ET
import pandas as pd
import xlwings as xw
import re

from spreadsheet_tools import load_reference_table
from spreadsheet_tools import append_data_sheet, save_and_close

from plan_report import load_aliases
from plan_report import Report
from build_sabr_plan_report import define_reports
from plan_data import DvhFile
from plan_data import Plan


base_path = Path.cwd()
data_path = base_path / 'Test Data'

from spreadsheet_tools import load_reference_table

# %% Load Laterality Table
reference_sheet_info = {'file_name': 'LateralityTable.xlsx',
                        'sheet_name': 'LateralityTable',
                        'base_path': data_path}
reference_table_info = {'starting_cell': 'A2', 'columns': 4}
LateralityLookup = load_reference_table(reference_sheet_info,
                                        reference_table_info)
LateralityLookup.set_index(['PlanLaterality','ReportItemLaterality','Symbol'],
                           inplace=True)

# %% Load Laterality Code Exceptions
reference_sheet_info['sheet_name'] = 'Laterality Code Exceptions'
reference_table_info['columns'] = 2
LateralityCodeExceptions = load_reference_table(reference_sheet_info,
                                                reference_table_info)
laterality_exceptions = set(LateralityCodeExceptions.Region)

# %% Load Report Definitions
report_definitions = define_reports(base_path, data_path)
report_name = 'SABR 48 in 4'
report = deepcopy(report_definitions[report_name])

# %% Load Plan File
dvh_file = data_path / 'test.dvh'
test_plan = Plan('test1', DvhFile(dvh_file))
#plan_file = DvhFile(dvh_file)
#(plan_parameters, plan_structures) = plan_file.load_data()


# %% Match Report and Plan Elements
default_pattern = '{Base} {LatIndicator}'
default_symbol = '~' # TODO replace symbol with type index

match_item = dict()

plan_laterality = test_plan.laterality
reference = report.report_elements['LungV20'].reference
item_laterality = reference['Laterality']
match_item['Base'] = reference['reference_name']
lookup_index = tuple([plan_laterality, item_laterality, default_symbol])
lat_indicator = LateralityLookup['Indicator'][lookup_index]

match_item['LatIndicator'] = lat_indicator
match_text = default_pattern.format(**match_item)

for element in report.report_elements:
    reference = element.reference
(match, not_matched) = report.match_elements(test_plan)
report.update_references(match, not_matched)
report.get_values(test_plan)
report.build()

print(report)

# %%
reference_sheet_info = {'file_name': 'Laterality.xlsx',
                        'sheet_name': 'Laterality Patterns',
                        'base_path': Path.cwd()}
reference_table_info = {'starting_cell': 'A2', 'columns': 3}
patterns = load_reference_table(reference_sheet_info, reference_table_info)
patterns.set_index(['Location', 'Symbol'], inplace=True)

# %% Load Symbols Table
reference_table_info = {'starting_cell': 'E2'}
symbols = load_reference_table(reference_sheet_info, reference_table_info)
symbols.set_index('Symbol', inplace=True)

# %% Save base structures
sheet_info = {'base_path': Path.cwd(),
              'file_name': 'Structure_base.xlsx',
              'sheet_name': 'Structure base',
              'starting_cell': 'A1',
              'new_file': True,
              'new_sheet': True,
              'replace': True
              }
saved = append_data_sheet(all_root_structures, add_index=True, **sheet_info)
save_and_close(saved)


#aliases_file = data_path / 'Aliases.xml'
#report_definition = data_path / 'ReportDefinitions.xml'
#alias_reference = load_aliases(aliases_file)
#report_tree = ET.parse(report_definition)
#report_root = report_tree.getroot()
#report_definitions = dict()
#for report_def in report_root.findall('Report'):
#    report = Report(report_def, alias_reference, data_path)
#    report_definitions[report.name] = report
