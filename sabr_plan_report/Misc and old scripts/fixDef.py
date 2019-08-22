from pathlib import Path
import xml.etree.ElementTree as ET


def load_items(file_path):
    data = dict()
    file_contents = file_path.read_text().splitlines()
    for text_line in file_contents:
        row_values = text_line.strip().split(',')
        (name, c1, c2) = row_values
        data[name] = (c1, c2)
    return data


def list_items(report):
    print('name,Cell')
    for element in report.findall('.//ReportItem'):
        name = element.attrib.get('name')
        cell_def = element.find(r'.//CellAddress')
        if cell_def is not None:
            cell = cell_def.text
        else:
            cell = ''
        print(name + ',' + cell)


def replace_cells(report_name, cell_file, cell_mod_log):
    report = report_list[report_name]
    c_path = Path.cwd() / 'Data' / cell_file
    cell_table = load_items(c_path)
    for e in report.findall('.//ReportItem'):
        item_name = e.attrib.get('name')
        cell = e.find(r'.//CellAddress')
        if cell is not None:
            (old, new) = cell_table[item_name]
            cell.text = new
            tmpl = 'name=\t{}\tOriginal Cell=\t{}\tOld Cell=\t{}\tNewCell=\t{}'
            cell_mod_log += tmpl.format(item_name, cell.text, old, new) + '\n'
    return cell_mod_log


# %%
d_path = Path.cwd() / 'Data' / 'ReportDefinitions.xml'
tree = ET.parse(d_path)
root = tree.getroot()
report_list = dict()
for report in root.findall('Report'):
    name = report.findtext('Name')
    report_list[name] = report

# %%
cell_mod_log = ''
cell_file = '48 in 4 cell fix.txt'
report_name = 'SABR 48 in 4'
cell_mod_log += report_name + '\n'
cell_mod_log = replace_cells(report_name, cell_file, cell_mod_log)

cell_file = '60 in 8 cell fix.txt'
report_name = 'SABR 60 in 8'
cell_mod_log += report_name + '\n'
cell_mod_log = replace_cells(report_name, cell_file, cell_mod_log)

cell_file = '54 in3 cell fix.txt'
report_name = 'SABR 54 in 3'
cell_mod_log += report_name + '\n'
cell_mod_log = replace_cells(report_name, cell_file, cell_mod_log)

# %%
task_path = Path.cwd() / 'Data' / 'CellMod_Log.txt'
data_path = Path.cwd() / 'Data' / 'ReportDefinitions modified.xml'
tree.write(data_path)
task_path.write_text(cell_mod_log)
# %%
# report = report_list[2]
# print(report.findtext('Name'))
# list_items(report)
