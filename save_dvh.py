'''Fill an Excel Spreadsheet with values from a DVH file.
'''


#%% imports etc.
from typing import Any, Dict, Tuple, List
from pathlib import Path
import pandas as pd
from dvh_config import load_config
from plan_data import load_plan, convert_units
import PySimpleGUI as sg
import xlwings as xw

import logging
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

# %%  Select File
def get_dvh_file(starting_path):
    form_rows = [[sg.Text('Select DVH File to Load')],
                 [sg.InputText(key='dvh_file'),
                  sg.FileBrowse(initial_folder=str(starting_path),
                                file_types=(('DVH Files', '*.dvh'),))],
                 [sg.Submit(), sg.Cancel()]]
    window = sg.Window('DVH File Selection', form_rows)
    button, values = window.read()
    window.close()
    dvh_file_name = values['dvh_file']
    if any((button != 'Submit', dvh_file_name == '')):
        sg.popup_error('Operation cancelled')
        dvh_file_path = None
    else:
        dvh_file_path = Path(dvh_file_name)
    return dvh_file_path


def get_save_file(starting_path: Path):
    if starting_path.is_dir():
        starting_dir = starting_path
        starting_file = ''
    else:
        starting_dir = starting_path.parent
        starting_file = str(starting_path)
    form_rows = [[sg.Text('Save Structure Data As:')],
                 [sg.InputText(key='save_file', default_text=starting_file),
                  sg.FileSaveAs(initial_folder=str(starting_dir),
                                file_types=(('Excel Files', '*.xlsx'),))],
                 [sg.Submit(), sg.Cancel()]]
    window = sg.Window('File Save', form_rows)
    button, values = window.read()
    window.close()
    save_file_name = Path(values['save_file'])
    if any((button != 'Submit', save_file_name == '')):
        save_file_path = None
    else:
        save_file_path = Path(save_file_name)
    return save_file_path


def save_data(save_file_path, sheet_name, dataset):
    exel_app = xw.apps.active
    if not exel_app:
        exel_app = xw.App(visible=None, add_book=False)
    if save_file_path.exists():
        workbook = exel_app.books.open(str(save_file_path))
    else:
        workbook = exel_app.books.add()
    sheet = workbook.sheets.add(sheet_name)
    if isinstance(dataset, dict):
        sheet.range('A1').options(dict).value = dataset
    else:
        sheet.range('A1').value = dataset
    workbook.save(str(save_file_path))
    return sheet


#%% Make Tables
def get_dvh(plan, prescribed_dose=1.0):
    for struc in plan.data_elements['Structure'].values():
        name = struc.name
        LOGGER.debug(f'Formatting DVH for structure:\t{struc.name}')
        data = struc.dose_data
        x_idx, y_idx, x_cnv = data.select_columns('cGy','Volume', 'cc')
        x_ini = data.dvh_curve[x_idx]
        x_unit = data.dvh_columns[x_idx]['Unit']
        if x_unit != 'cGy':
            x_cgy = [convert_units(ds, 'x_unit', 'cGy', dose=prescribed_dose)
                     for ds in x_ini]
        else:
            x_cgy = list(x_ini)
        y_ini = data.dvh_curve[y_idx]
        y_unit = data.dvh_columns[y_idx]['Unit']
        if y_unit != 'cc':
            str_vol = struc.structure_properties['Volume'].element_value
            if not str_vol:
                continue
            y_cc = [convert_units(vl, y_unit, 'cc', volume=str_vol)
                    for vl in y_ini]
        structure = pd.DataFrame({'Dose_cGy': x_cgy, name: y_cc})
        structure.set_index('Dose_cGy', inplace=True)
        yield structure


def get_structures(plan):
    structure_dict = dict()
    for struc in plan.data_elements['Structure'].values():
        name = struc.name
        struc_prop = {ky: vl.element_value
                      for ky,vl in struc.structure_properties.items()}
        structure_dict[name] = struc_prop
    structure_params = pd.DataFrame(structure_dict)
    return structure_params

def make_tables(plan):
    prescribed_dose = plan.prescription_dose.element_value
    dvh_series = [struct for struct in get_dvh(plan, prescribed_dose)]
    dvh_table = pd.concat(dvh_series, axis=1)
    structure_table = get_structures(plan)
    return structure_table, dvh_table

#%% Main
def main():
    '''Test
    '''
    # Load Config File Data
    base_path = Path.cwd()
    dvh_path = base_path / r'Test Data\SABR_Plan_Report_Testing\DVH Data Feb 14 2018.dvh'
    config_file = 'SaveDVHConfig.xml'
    config = load_config(base_path, config_file)

    plan = load_plan(config, dvh_path)
    structure_table, dvh_table = make_tables(plan)

    save_file_name='structure_data.xlsx'
    save_file = dvh_path / save_file_name
    save_file_path = get_save_file(save_file)
    save_data(save_file_path, 'Structures', structure_table)
    save_data(save_file_path, 'DVH', dvh_table)

if __name__ == '__main__':
    main()
