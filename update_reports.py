#!/usr/bin/env python
from pathlib import Path
from typing import Any, Dict, Tuple, List
import xml.etree.ElementTree as ET
import PySimpleGUI as sg
from build_plan_report import load_config, update_reports

'''
    Update the Report Definition Pickle file
'''

def report_dir_list(base_path: Path, report_dirs):
    '''Generate a string list of directories containing report definitions.
    The list is obtained from the Config .xml file.
    The directories in the string list replace the top directory path,
    given by base_str, with: ".\".
    Arguments:
        report_dirs {List[Path, str]} -- List of report directory paths.
        base_path {Path} -- A path to the top directory referenced.
    '''
    base_str = str(base_path)
    report_locations = list()
    for location in report_dirs:
        report_dir = Path(location).resolve()
        report_dir_str = str(report_dir).replace(base_str, '.')
        report_locations.append(report_dir_str)
    return report_locations

def get_report_dir_list(config: ET.Element)->List[Path]:
    '''Generate a list of directories containing report definitions.
    The list is obtained from the Config .xml file.
    Arguments:
        config {ET.Element} -- Config .xml file Element.
    Returns:
        List[Path] -- A list of directories containing report definitions.
    '''
    default_directories = config.find(r'./DefaultDirectories')
    rpt_dir = default_directories.find('ReportDefinitions')
    report_dirs = [Path(dr.text).resolve()
                   for dr in rpt_dir.findall('Directory')]
    return report_dirs


def selection_window(report_locations: List[str], base_str: str = '')->sg.Window:
    '''Generate the window used to select directories containing report
    definitions.
    '''
    form_rows = [[sg.Text('Select Folders Containing Evaluation Reports')],
                 [sg.Listbox(key='ReportDirs',
                             select_mode=sg.LISTBOX_SELECT_MODE_MULTIPLE,
                             auto_size_text=False,
                             size=(40, 5),
                             values=report_locations),
                  sg.VerticalSeparator(),
                  sg.Column([
                      [sg.Button(button_text='Delete', size=(15, 1), pad=(10, 5))],
                      [sg.Button(button_text='Add', size=(15, 1), pad=(10, 5))],
                      ])
                 ],
                 [sg.InputText(key='NewReportDir'),
                  sg.FolderBrowse(target='NewReportDir',
                                  initial_folder=base_str)],
                 [sg.Submit(), sg.Cancel()]
                ]
    window = sg.Window('Update Report Definitions', form_rows)
    return window


def select_locations(report_locations, base_path):
    base_str = str(base_path)
    window = selection_window(report_locations, base_str)
    done = False
    dir_list = window['ReportDirs']
    while not done:
        event, values = window.read(timeout=200)
        if event == sg.TIMEOUT_KEY:
            continue
        elif event in 'Cancel':
            done=True
            report_locations = None
        elif event in 'Submit':
            done=True
            report_locations = [Path(dir) for dir in dir_list.GetListValues()]
        elif event in 'Delete':
            remove_items = values['ReportDirs']
            updated_list = [dir for dir in dir_list.GetListValues()
                            if dir not in remove_items]
            dir_list.Update(values=updated_list)
            window.refresh()
        elif event in 'Add':
            add_item = values['NewReportDir']
            report_dir = Path(add_item).resolve()
            report_dir_str = str(report_dir).replace(base_str, '.\\')
            updated_list = set(dir_list.GetListValues())
            updated_list.add(report_dir_str)
            dir_list.Update(values=list(updated_list))
            window.refresh()
    window.close()
    return report_locations



def update_report_definitions(config, base_path, report_locations=None):
    '''Define Folder Paths, load report and plan data.
    '''
    default_directories = config.find(r'./DefaultDirectories')
    pickle_file = Path(default_directories.findtext('ReportPickleFile'))
    if report_locations:
        report_list = report_dir_list(base_path, list(report_locations))
    else:
        report_dirs = get_report_dir_list(config)
        report_list = report_dir_list(base_path, report_dirs)

    # Call GUI to select Report Definition Directories
    new_report_locations = select_locations(report_list, base_path)
    if new_report_locations:
        report_paths = [Path(dir).resolve() for dir in new_report_locations]
        report_definitions = update_reports(config, report_paths, pickle_file)
    else:
        report_definitions = None
    return report_definitions


#%% Main
def main():
    '''Define Folder Paths, load report and plan data.
    '''
    base_path = Path.cwd().resolve()
    #%% Load Config file and Report definitions
    config_file = 'PlanEvaluationConfig.xml'
    config = load_config(base_path, config_file)

    report_definitions = update_report_definitions(config, base_path)
    return report_definitions



if __name__ == '__main__':
    main()

