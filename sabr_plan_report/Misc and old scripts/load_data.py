"""
Created on Sun Mar 18 16:07:52 2018

@author: Greg
"""
from pathlib import Path
import xml.etree.ElementTree as ET

def load_report_definition():
    # TODO load_report_definition is likely not used.;
    plan_tree = ET.parse(r'./Test Data/PlanDefinitions.xml')
    plan_root = report_tree.getroot()

    report_tree = ET.parse(r'./Test Data/ReportDefinitions.xml')
    report_root = report_tree.getroot()
    report_def = report_root.find('Report')

    report_name = report_def.findtext('Name')
    template_file = report_def.findtext(r'./FilePaths/Template/File')
    worksheet = report_def.findtext(r'./FilePaths/Template/WorkSheet')
    save_path = report_def.findtext(r'./FilePaths/Save/Path')
    save_file_name = report_def.findtext(r'./FilePaths/Save/File')
    save_file_path = Path(save_path) / save_file_name
    save_worksheet = report_def.findtext(r'./FilePaths/Save/WorkSheet')

    #report_items = report_def.findall('ReportItemList')

    item_list = report_def.findall('ReportItemList')[0]
    report_item = item_list.find('ReportItem')
    reference = report_item.find('PlanReference')
    for element in reference.findall(r'./*'):
        print('Item: {}\t\tValue: {}'.format(element.tag, element.text))

def load_items(file_path):
    '''Read in data from a comma separated text file.
    The first line of the file defines the variable names.
    If a line has more elements than the number of variables then the last
    variable is assigned a list of trhe remaining elements.
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

