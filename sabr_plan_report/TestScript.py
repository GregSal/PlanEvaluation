from pathlib import Path
from copy import deepcopy
import xml.etree.ElementTree as ET
import pandas as pd
import xlwings as xw
import re

from spreadsheet_tools import load_reference_table, append_data_sheet, save_and_close

# %% Load Structure Laterality
reference_sheet_info = {'file_name': 'Laterality.xlsx',
                        'sheet_name': 'Structure Laterality',
                        'base_path': Path.cwd()}
reference_table_info = dict()

Structures = load_reference_table(reference_sheet_info, reference_table_info)
structure_data = Structures.drop_duplicates('StructureID')
#structure_data.set_index('StructureID', inplace=True)

# %% Make patterns
lateral_structures = Structures.dropna('rows', subset=['Laterality'])
patterns = list(lateral_structures['Laterality Expression'])
# FIXME the laterality pattern should be enclosed in brackets
#laterality = [p.split(')', 1)[1] for p in patterns]
#laterality = [l.split('(', 1)[0] for l in laterality]
#laterality = [l.replace(')', '') for l in laterality]
patterns = [p.replace(l, '(' + l + ')') for p,l in zip(patterns, laterality)]

strings = list(lateral_structures['StructureID'])
# %% Make roots
parts = list()
structure = list()
for p,s in zip(patterns, strings):
    match = re.search(p,s, flags=re.IGNORECASE)
    parts.append(match.groups())
    structure.append(match.string)
root_structure = pd.DataFrame(parts, columns=['BaseStructure','Pattern','StructureSuffix'])
root_structure['StructureID'] = structure
#root_structure.set_index('StructureID', inplace=True)
#structures_indexed = lateral_structures.set_index('StructureID')
all_root_structures = pd.merge(Structures, root_structure, how='outer', on='StructureID')

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

# %%
structure_data = Structures[['StructureID', 'Laterality Indicator 1', 'Laterality', 'VolumeType', 'TemplateCategory']]
structure_data = structure_data.drop_duplicates()
lateral_structures = structure_data.dropna('rows', subset=['Laterality'])
#left_structures = structure_data[structure_data.Laterality.str.contains('Left')]

s = lateral_structures.StructureID
t=pd.DataFrame()
for a in list(patterns.loc[:,'Pattern']):
    d = '^' + a.replace('.*','(.*)') +'$'
    e = d.replace('(.*)','\\1',1)
    e = e.replace('(.*)','\\2',1)
    n = '\\2' in e
    b = '~'*a.count('~')
    c = list(symbols.loc[b,:].dropna('rows'))
    f = [d.replace(b,r) for r in c]
    for g in f:
        s = s.str.replace(g,e, case=False)
        t1 = s.str.split(g, expand=True)
        t = pd.concat([t, t1])
        


# %%
#b = re.findall('.*(~{1,3}).*',a)[0]
#e = ['^(.*)_B$', '^(.*)_R$', '^(.*)_L$']

f = a.replace('.*','\\1')

c = str(symbols.loc[b,'Left'])
d = a.replace('.*','(.*)')
e = d.replace(a.replace('.*',''), '(' + a.replace('.*','') + ')')
f = re.sub(b,c,e)
g = re.compile(d, flags=re.IGNORECASE)


s = left_structures.StructureID.str.replace(e[0],f, case=False)
s = left_structures.StructureID.str.replace(e[1],f, case=False)
s = left_structures.StructureID.str.replace(e[2],f, case=False)

from plan_report import load_aliases
from plan_report import Report
from build_sabr_plan_report import define_reports
from plan_data import DvhFile
from plan_data import Plan

base_path = Path.cwd()
data_path = base_path / 'Test Data'

#aliases_file = data_path / 'Aliases.xml'
#report_definition = data_path / 'ReportDefinitions.xml'
#alias_reference = load_aliases(aliases_file)
#report_tree = ET.parse(report_definition)
#report_root = report_tree.getroot()
#report_definitions = dict()
#for report_def in report_root.findall('Report'):
#    report = Report(report_def, alias_reference, data_path)
#    report_definitions[report.name] = report

report_definitions = define_reports(base_path, data_path)
dvh_file = data_path / 'test.dvh'

#plan_file = DvhFile(dvh_file)
#(plan_parameters, plan_structures) = plan_file.load_data()

test_plan = Plan('test1', DvhFile(dvh_file))
report_name = 'SABR 48 in 4'
report = deepcopy(report_definitions[report_name])

(match, not_matched) = report.match_elements(test_plan)
report.update_references(match, not_matched)
report.get_values(test_plan)
report.build()

print(report)