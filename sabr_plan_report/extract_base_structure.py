# -*- coding: utf-8 -*-
"""
Created on Thu Aug  8 14:15:32 2019

@author: gsalomon

Extract base structures from structure names.
"""

from pathlib import Path
import pandas as pd
import re

from spreadsheet_tools import load_reference_table, append_data_sheet
from spreadsheet_tools import save_and_close

# %% Load Structure Laterality
reference_sheet_info = {'file_name': 'Laterality.xlsx',
                        'sheet_name': 'Structure Laterality',
                        'base_path': Path.cwd()}
reference_table_info = dict()
Structures = load_reference_table(reference_sheet_info, reference_table_info)
structure_data = Structures.drop_duplicates('StructureID')

# %% Make patterns
lateral_structures = Structures.dropna('rows', subset=['Laterality'])
patterns = list(lateral_structures['Laterality Expression'])
strings = list(lateral_structures['StructureID'])

parts = list()
structure = list()
for p,s in zip(patterns, strings):
    match = re.search(p,s, flags=re.IGNORECASE)
    groups = match.groupdict()
    groups['StructureID'] = match.string
    parts.append(groups)

root_structure = pd.DataFrame(parts)
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
saved = append_data_sheet(all_root_structures, **sheet_info)
save_and_close(saved)
