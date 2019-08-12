# -*- coding: utf-8 -*-
"""
Created on Thu Aug  8 14:15:32 2019

@author: gsalomon

Create Laterality Table .xml file
"""

from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd

from spreadsheet_tools import load_reference_table

# %% Load Laterality Table
data_path = Path.cwd() / 'Structure and plan info'
reference_sheet_info = {'file_name': 'Laterality.xlsx',
                        'sheet_name': 'Structure Laterality Grid',
                        'base_path': data_path}
reference_table_info = {'starting_cell': 'H2', 'columns': 'expand'}
TableData = load_reference_table(reference_sheet_info, reference_table_info)

# %%
table = ET.Element('LateralityTable')
PlanLaterality = TableData.groupby('Plan Laterality')
for plan_name, Plan in PlanLaterality:
    plan_element = ET.SubElement(table, 'PlanLaterality')
    value = ET.SubElement(plan_element, 'Value')
    value.text = plan_name
    ReportItemLaterality = Plan.groupby('Report Item Laterality')
    for report_name, Report in ReportItemLaterality:
        report_element = ET.SubElement(plan_element, 'ReportItemLaterality')
        value = ET.SubElement(report_element, 'Value')
        value.text = report_name
        Symbol = Report.groupby('Symbol')
        for symbol_name, Sb in Symbol:
            symbol_element = ET.SubElement(report_element, 'Symbol')
            value = ET.SubElement(symbol_element, 'Value')
            value.text = symbol_name
            for Indicator in list(Sb.loc[:,'Indicator']):
                indicator_element = ET.SubElement(report_element, 'Indicator')
                indicator_element.text = Indicator

save_file = data_path / 'Laterality Table.xml'
table_xml = ET.ElementTree(table)
table_xml.write(str(save_file))
