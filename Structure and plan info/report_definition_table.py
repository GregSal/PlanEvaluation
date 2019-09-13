from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd
from plan_report import Report

#%% Define Folder Paths
base_path = Path.cwd()
test_path = base_path / 'SABR_Plan_Report_Testing'
report_definition_file = test_path / 'TestReportDefinitions.xml'
results_path = test_path / 'Output'

# %%
tree = ET.parse(report_definition_file)
root = tree.getroot()

for report_def in root.findall('Report'):
    report = Report(report_def, template_path=test_path, save_path=results_path)
    report_data = pd.DataFrame(report.table_output())
    file_name = '{} Report_table.xls'.format(report.name)
    report_table_file = results_path / file_name
    report_data.to_excel(report_table_file, sheet_name=report.name)

