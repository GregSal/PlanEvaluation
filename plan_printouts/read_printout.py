# -*- coding: utf-8 -*-
"""
Created on Wed Oct  2 22:38:15 2019

@author: Greg
Read Eclipse Text Print
"""

# %% Imports etc
from pathlib import Path
from typing import TypeVar, Dict, List, Tuple, TextIO, Any
import pandas as pd
import numpy as np
import utilities_path
import PySimpleGUI as sg

from spreadsheet_tools import create_output_file, save_data_to_sheet, get_data_sheet
from text_utilities import read_file_header, next_line, EOF


HeaderValue = TypeVar('HeaderValue', str, float, int)
Data = TypeVar('Data', pd.DataFrame, pd.Series, np.ndarray)


def load_plan_data(file: TextIO)->Dict[str, Any]:
    start_of_field = 'FieldId'
    plan_dict = dict()
    plan_dict = read_file_header(file, plan_dict, stop_marker=start_of_field,
                                 step_back=True)
    del plan_dict[start_of_field]
    return plan_dict


def load_initial_field_data(file: TextIO, plan_dict: Dict[str, Any],
                            start_of_point: str, end_of_field: str
                            )->Tuple[Dict[str, Any]]:
    field_markers = [start_of_point, end_of_field]
    field_data = dict(PlanId=plan_dict.get('PlanId'),
                      Course=plan_dict.get('CourseId'))
    field_data = read_file_header(file, field_data, stop_marker=field_markers,
                                  step_back=True)
    if start_of_point in field_data:
        del field_data[start_of_point]
    return field_data


def load_point_data(file: TextIO, field_data: Dict[str, Any],
                    point_list: List[Dict[str, Any]],
                    end_of_point: str, start_of_plan_calculation: str
                    )->List[Dict[str, Any]]:
    point_markers = [end_of_point, start_of_plan_calculation]
    while True:
        point_data = dict(field_name=field_data['FieldId'])
        point_data = read_file_header(file, point_data,
                                      stop_marker=point_markers,
                                      step_back=False)
        if start_of_plan_calculation in point_data:
            del point_data[start_of_plan_calculation]
            break
        point_list.append(point_data)
    return point_list


def load_field_calculation_info(file,
                                field_data: Dict[str, Any])->Dict[str, Any]:
    position = file.tell()
    line = next_line(file)
    calc_info = ''
    while 'FieldCalculationInfo' in line:
        text_line = line.strip(' \n')
        calc_info += text_line.replace('FieldCalculationInfo;', '')
        position = file.tell()
        line = next_line(file)
    file.seek(position)
    field_data['FieldCalculationInfo'] = calc_info
    return field_data


def reached_end_of_fields(file, end_of_fields_marker)->bool:
    position = file.tell()
    line = next_line(file)
    if end_of_fields_marker in line:
        file.seek(position)
        return True
    file.seek(position)
    return False


def load_field_data(file: TextIO, plan_dict: Dict[str, Any])->Tuple[Dict[str, Any]]:
    start_of_point = 'RefPoints'
    end_of_field = 'FieldCalculationInfo'
    field_markers = [start_of_point, end_of_field]
    end_of_point = 'FieldRefPointEffectiveDepth'
    start_of_plan_calculation = 'FieldCalculationTimestamp'

    field_list = list()
    point_list = list()
    try:
        while True:
            field_data = load_initial_field_data(file, plan_dict,
                                                 start_of_point, end_of_field)
            point_list = load_point_data(file, field_data, point_list,
                                         end_of_point,
                                         start_of_plan_calculation)
            field_data = read_file_header(file, field_data,
                                          stop_marker=field_markers,
                                          step_back=True)
            field_data = load_field_calculation_info(file, field_data)
            field_list.append(field_data)
            if reached_end_of_fields(file, 'FractionationId'):
                break
        next_line(file) # skip FractionationId line
        field_label = {'FieldId': 'Total'}
        point_list = load_point_data(file, field_label, point_list,
                                     end_of_point='RefPointPatientVolumeId',
                                     start_of_plan_calculation='ZZZZZZZZZ')
    except EOF:
        pass
    field_data = pd.DataFrame(field_list)
    point_data = pd.DataFrame(point_list)
    return field_data, point_data


def read_printout_file(printout_file_path: Path):
    '''read a printout file and save the resulting data to a spreadsheet.
    '''
    with printout_file_path.open() as file:
        plan_dict = load_plan_data(file)
        (field_data, point_data) = load_field_data(file, plan_dict)
    return plan_dict, field_data, point_data


def process_field_data(field_data: pd.DataFrame)->pd.DataFrame:
    field_data_columns = {
            'PlanId': 'Plan',
            'Course': 'Course',
            'FieldId': 'Field',
            'FieldName': 'Field Name',
            'FieldMachineId': 'Linac',
            'FieldEnergyMode': 'Energy',
            'FieldTechnique': 'Technique',
            'FieldMonitorUnits': 'MUs',
            'FieldRefDose': 'Field Dose',
            'FieldSAD': 'SAD',
            'FieldSSD': 'Field SSD',
            'FieldGantryAngle': 'Gantry',
            'FieldCollimatorAngle': 'Collimator',
            'FieldTableAngle': 'Couch',
            'FieldIsocentreX': 'Iso X',
            'FieldIsocentreY': 'Iso Y',
            'FieldIsocentreZ': 'Iso Z',
            'FieldNormFactor': 'Norm Factor',
            'FieldWeightFactor': 'Field Weight',
            'FieldCalculationWarning': 'Warning'
            }
    field_data = field_data.rename(columns=field_data_columns)
    column_select = tuple(name for name in field_data_columns.values() 
                          if name in field_data.columns)
    field_data = field_data.loc[:, column_select]
    field_data['Field Side'] = field_data.loc[:,'Field Name'].str.split(expand=True)[0]
    return field_data


def process_point_data(point_data: pd.DataFrame,
                       field_data: pd.DataFrame)->pd.DataFrame:
    point_data_columns = {
            'field_name': 'Field',
            'RefPointId': 'Point',
            'FieldDose': 'Dose',
            'FieldRefPointSSD': 'SSD',
            'FieldRefPointPointDepth': 'Depth',
            'FieldRefPointEffectiveDepth': 'Efective Depth',
            'RefPointX': 'X',
            'RefPointY': 'Y',
            'RefPointZ': 'Z',
            'RefPointTotalDose': 'Total Dose'
            }
    point_data = point_data.rename(columns=point_data_columns)
    column_select = tuple(name for name in point_data_columns.values() 
                          if name in point_data.columns)
    point_data = point_data.loc[:, column_select]
    point_total = point_data.Field.isin(['Total'])
    if any(point_total):
        point_data.loc[point_total,'Dose'] = point_data.loc[point_total,'Total Dose']
        point_location = point_data.loc[:, ('Point', 'X', 'Y', 'Z')].dropna()
        point_data.drop(['Total Dose', 'X', 'Y', 'Z'], axis=1, inplace=True)
    else:
        point_location = pd.DataFrame()
    point_data.loc[point_data['Efective Depth'].isin(['-']),'Efective Depth'] = 0
    point_data.loc[point_data.Depth.isin(['-']),'Depth'] = 0
    point_data.loc[point_data.SSD.isin(['-']),'SSD'] = 100
    point_data.Depth = point_data.loc[point_data.Depth.notna(),'Depth'].apply(round)
    field_merge = [
        'Plan',
        'Course',
        'Field',
        'Field Name',
        'Energy',
        'MUs',
        'Field Dose',
        'SAD',
        'Field SSD',
        'Iso X',
        'Iso Y',
        'Iso Z',
        'Norm Factor',
        'Field Weight'
        ]
    point_data = pd.merge(point_data, field_data.loc[:, field_merge],
                          how='left', on='Field')
    return point_data, point_location


def point_dose_difference(point_data):
    field_selection = ['Field', 'Depth','Side', 'Field SSD', 'Dose']
    index_selection = ['Field', 'Field SSD', 'Depth']
    point_dose = point_data.loc[point_data.Depth.notna(),field_selection]
    point_dose.set_index(index_selection, inplace=True)

    thin = point_dose.Side.str.contains('Thin')
    point_dose['Thin'] = point_dose.Dose[thin]
    thick = point_dose.Side.str.contains('Thick')
    point_dose['Thick'] = point_dose.Dose[thick]
    center = point_dose.Side.str.contains('Center')
    point_dose['Center'] = point_dose.Dose[center]

    point_dose.drop(['Side', 'Dose'], axis=1, inplace=True)
    point_dose = point_dose.dropna()
    point_dose = point_dose.drop_duplicates()

    point_dose['difference'] = point_dose.apply(max, axis=1)-point_dose.apply(min, axis=1)
    point_dose.reset_index(inplace=True)
    return point_dose


def add_plan_variables(plan_dict, data):
    plan_variables = [
        'PatientId',
        'ImageId',
        'ImageName',
        'ImageUserOrigin',
        'PlanModificationDate',
        'StructureId',
        'StructureName',
        'PlanNormValue',
        'PrescribedDose',
        'Fractions'
        ]
    for var in plan_variables:
        data[var] = plan_dict[var]
    return data

def save_printout_file(plan_dict: Dict[str, Any],
                       field_data, point_data, point_location,
                       save_file_path: Path):
    '''Save the resulting data to a spreadsheet.
    '''
    workbook = create_output_file(save_file_path)
    get_data_sheet(workbook, 'plan').range('A1').value = plan_dict
    save_data_to_sheet(field_data, workbook, 'fields')
    save_data_to_sheet(point_data, workbook, 'points')
    save_data_to_sheet(point_location, workbook, 'Point Location')
    save_data_to_sheet(dose_difference, workbook, 'Dose Difference')

# %%  Select File
def get_printout_file(starting_path):
    form_rows = [[sg.Text('Select Printout File to Load')],
                 [sg.InputText(key='printout_file'),
                  sg.FileBrowse(initial_folder=str(starting_path))],
                 [sg.Submit(), sg.Cancel()]]

    window = sg.Window('File Selection', form_rows)
    button, values = window.read()
    window.close()        
    printout_file_name = values['printout_file']
    if any((button != 'Submit', printout_file_name == '')):
        sg.popup_error('Operation cancelled')
        printout_file_path = None
    else:
        printout_file_path = Path(printout_file_name)
    return printout_file_path

def get_save_file(starting_path):
    form_rows = [[sg.Text('Save Printout File As:')],
                 [sg.InputText(key='printout_file'),
                  sg.FileSaveAs(initial_folder=str(starting_path))],
                 [sg.Submit(), sg.Cancel()]]

    window = sg.Window('File Save', form_rows)
    button, values = window.read()
    window.close()
    printout_file_name = values['printout_file']
    if any((button != 'Submit', printout_file_name == '')):
        sg.popup_error('Operation cancelled')
        save_file_path = None
    else:
        save_file_path = Path(printout_file_name)
    return save_file_path

def main():
    '''Basic test code
    '''
    base_path = Path.cwd()
    data_path = base_path / r'..\PlanEvaluation\Test Data\Printout Data'
    #printout_file_path = data_path / 'AG30N6XF20.txt'
    save_file_path = data_path / 'Printout_data_tables.xlsx'
    
    printout_file_path = get_printout_file(data_path)
    plan_dict, field_data, point_data = read_printout_file(printout_file_path)
    field_data = process_field_data(field_data)
    (point_data, point_location) = process_point_data(point_data, field_data)
    #dose_difference = point_dose_difference(point_data)
    #dose_difference = add_plan_variables(plan_dict, dose_difference)

    save_file_path = get_save_file(data_path)
    save_printout_file(plan_dict, field_data, point_data, point_location, save_file_path)


if __name__ == '__main__':
    main()