'''Run tests of the GUI interface
'''

#%% imports etc.
import sys
import os
from pathlib import Path
from operator import attrgetter
import textwrap as tw

from typing import Optional, Union, Any, Dict, Tuple, List, Set
from typing import NamedTuple
from copy import deepcopy
from functools import partial

import xml.etree.ElementTree as ET

#import tkinter.filedialog as tkf
#import tkinter as tk
#from tkinter import messagebox

import PySimpleGUI as sg

import xlwings as xw

from build_plan_report import initialize, read_report_files, load_config, find_plan_files
from plan_report import Report, ReferenceGroup, MatchList
from plan_data import DvhFile, Plan, PlanItemLookup, PlanElements, get_dvh_list, PlanDescription


Values = Dict[str, List[str]]
ConversionParameters = Dict[str, Union[str, float, None]]

class IconPaths(dict):
    '''Match Parameters for a PlanReference.
        Report Item name, match status, plan item type, Plan Item name
    Attributes:
        match_icon {Path} -- Green Check mark
        not_matched_icon {str} -- The type of PlanElement.  Can be one of:
            ('Plan Property', Structure', 'Reference Point', 'Ratio')
        match_status: {str} -- How a plan value was obtained.  One of:
            One of Auto, Manual, Direct Entry, or None
        plan_Item: {str} -- The name of the matched element from the Plan.
    '''
    def __init__(self, icon_path):
        '''Initialize the icon paths.
        Attributes:
            icon_path {Path} -- The path to the Icon Directory
        Contains the following Icon references:
            match_icon {Path} -- Green Check mark
            not_matched_icon {Path} -- Red X
            changed_icon {Path} -- Yellow Sun
        '''
        super().__init__()
        # Icons
        self['match_icon'] = icon_path / 'Checkmark.png'
        self['not_matched_icon'] = icon_path / 'Error_Symbol.png'
        self['changed_icon'] = icon_path / 'emblem-new'

    def path(self, icon_name):
        '''Return a string path to the icon.
        Attributes:
            icon_name {str} -- The name of an icon in the dictionary
        '''
        icon_path = self.get(icon_name)
        if icon_path:
            return str(icon_path)
        return None




#%% Plan Header
def create_plan_header(desc: PlanDescription)->sg.Frame:
    '''Create a Frame GUI element containing patient and plan info.
    Arguments:
        desc {PlanDescription} -- Summary data for the plan.
    Returns:
        sg.Frame -- A group of text GUI s with Dose, Course,
        export date, patient name and ID for the plan.
    '''
    # Set Dose Text
    dose_value=desc.dose
    fractions_value=desc.fractions
    if dose_value:
        if fractions_value:
            dose_pattern =  '{dose:>4.1f}cGy in {fractions:>2d} fractions'
            dose_text = dose_pattern.format(dose=dose_value,
                                            fractions=fractions_value)
        else:
            dose_pattern =  '{dose:>4.1f}cGy'
            dose_text = dose_pattern.format(dose=dose_value)
    else:
        dose_text = ''
    # Set Patient Header
    pt_id = desc.patient_id
    try:
        id_value = int(pt_id)
    except (ValueError, TypeError):
        id_value = str(pt_id)
        id_pattern = '{id:>8s}'
    else:
        id_pattern = '{id:0>8n}'
    finally:
        id_text = id_pattern.format(id=id_value)
    patient_desc = [
        [sg.Text('Name:', size=(6,1)), sg.Text(desc.patient_name, key='pt_name_text')],
        [sg.Text('ID:', size=(6,1)), sg.Text(id_text, key='id_text')]
        ]
    patient_header = sg.Frame('Patient:', patient_desc,
                              key='patient_header',
                              title_location=sg.TITLE_LOCATION_TOP_LEFT,
                              font=('Calibri', 12),
                              element_justification='left')
    # Set Main Label
    plan_title = sg.Text(text=desc.plan_name,
                         key='plan_title',
                         font=('Calibri', 14, 'bold'),
                         pad=((5, 0), (0, 10)),
                         justification='center', visible=True)
    header_layout = [
        [plan_title],
        [sg.Text('Dose:', size=(8,1)), sg.Text(dose_text, key='dose_text')],
        [sg.Text('Course:', size=(8,1)), sg.Text(desc.course, key='course_text')],
        [sg.Text('Exported:', size=(8,1)), sg.Text(desc.export_date, key='exported_text')],
        [patient_header]
        ]
    plan_header = sg.Frame('Plan', header_layout, key='plan_header',
                           title_location=sg.TITLE_LOCATION_TOP,
                           font=('Arial Black', 14, 'bold'),
                           element_justification='center',
                           relief=sg.RELIEF_GROOVE, border_width=5)
    return plan_header

#%% Report Header
def create_report_header(report: Report)->sg.Frame:
    wrapped_desc = tw.fill(report.description, width=40)
    wrapped_file = tw.fill(report.template_file.name, width=30)
    wrapped_sheet = tw.fill(report.worksheet, width=30)
    template_layout = [
        [sg.Text('File:', size=(12,1)),
         sg.Text(wrapped_file, key='template_file')],
        [sg.Text('WorkSheet:', size=(12,1)),
         sg.Text(wrapped_sheet, key='template_sheet')],
        ]
    report_title = sg.Text(text=report.name,
                           key='report_title',
                           font=('Calibri', 14, 'bold'),
                           justification='center',
                           visible=True)
    report_desc = sg.Text(text=wrapped_desc,
                          key='report_desc',
                          visible=True)
    template_header = sg.Frame('Template:', template_layout,
                                   key='template_header',
                                   title_location=sg.TITLE_LOCATION_TOP_LEFT,
                                   font=('Calibri', 12),
                                   element_justification='left')
    header_layout = [
        [report_title],
        [report_desc],
        [template_header]
        ]
    report_header = sg.Frame('Report', header_layout,
                             key='report_header',
                             title_location=sg.TITLE_LOCATION_TOP,
                             font=('Arial Black', 14, 'bold'),
                             element_justification='center',
                             relief=sg.RELIEF_GROOVE, border_width=5)
    return report_header



#%% Plan Selector

def plan_selector(plan_list: List[PlanDescription]):
    '''Plan Selection GUI
    '''
    patients = {plan.name_str() for plan in plan_list}
    patient_list = sorted(patients)
    column_names = ['Patient', 'Plan Info', 'Course', 'Dose', 'Fractions', 'File', 'Type']
    show_column = [False, False, False, True, False] # Show only Fractions
    column_widths = [30, 30, 5, 5, 30, 10]
    tree_settings = dict(key='Plan_tree',
                         headings=column_names,
                         visible_column_map=show_column,
                         col0_width=30,
                         col_widths=column_widths,
                         auto_size_columns=False,
                         justification='left',
                         num_rows=5,
                         font=('Verdana', 104, 'normal'),
                         show_expanded=True,
                         select_mode='browse',
                         enable_events=True)
    # Tree data
    # Plan Files for selecting
    treedata = sg.TreeData()
    for patient in patient_list:
        treedata.Insert('', patient, patient, [patient])
    for plan in plan_list:
        patient = plan.name_str()
        plan_info = plan.plan_str()
        values_list = [patient, plan_info, plan.course, plan.dose, plan.fractions, plan.plan_file.name, plan.file_type]
        treedata.Insert(patient, plan_info, plan_info, values_list)
    return sg.Tree(data=treedata, **tree_settings)




#%% GUI settings
def main_window(icons: IconPaths, plan_elements: PlanItemLookup,
                 reference_data: List[ReferenceGroup])->sg.Window:
    plan_header = create_plan_header(desc)
    report_header = create_report_header(report)
    w = sg.Window('Plan Evaluation',
        layout=[[plan_header, report_header]],
        default_element_size=(45, 1),
        default_button_element_size=(None, None),
        auto_size_text=None,
        auto_size_buttons=None,
        location=(None, None),
        size=(None, None),
        element_padding=None,
        margins=(None, None),
        button_color=None,
        font=None,
        progress_bar_color=(None, None),
        background_color=None,
        border_depth=None,
        auto_close=False,
        auto_close_duration=3,
        icon=None,
        force_toplevel=False,
        alpha_channel=1,
        return_keyboard_events=False,
        use_default_focus=True,
        text_justification=None,
        no_titlebar=False,
        grab_anywhere=False,
        keep_on_top=False,
        resizable=False,
        disable_close=False,
        disable_minimize=False,
        right_click_menu=None,
        transparent_color=None,
        debugger_enabled=False,
        finalize=True,
        element_justification="left")
    return window


#%% Main
def main():
    '''Define Folder Paths, load report and plan data.
    '''
    base_path = Path.cwd() / '..'
    test_path = base_path / 'GUI' / 'Testing'
    data_path = test_path
    results_path = base_path / 'GUI' / 'Output'
    icon_path = base_path / 'GUI' / 'icons'
    icons = IconPaths(icon_path)

    #%% Initial Plan and Report Settings
    config_file = 'TestPlanEvaluationConfig.xml'
    desc = PlanDescription(Path.cwd(), 'DVH', 'AA, BB', '11', 'LUNR', 'C1',
                           4800, 4,  'Tuesday, August 29, 2017 16:19:54')
    report_name = 'SABR 54 in 3'
    report_description = 'SABR Plan Evaluation Sheet for 12Gy/fr Schedules '
    report_description += '(48 Gy in 4F) or (60Gy/5F)'

    #%% Load Config file and Report definitions
    (config, report_parameters) = initialize(data_path, config_file)
    report_definitions = read_report_files(**report_parameters)
    report = deepcopy(report_definitions[report_name])

    #%% Load list of Plan Files
    plan_list = find_plan_files(config, test_path)

    plan_header = create_plan_header(desc)
    report_header = create_report_header(report)



    w.Read()

    report.match_elements(plan)
    (report, plan, num_updates) = manual_match(report, plan, icons)


#%% Run Tests

#if __name__ == '__main__':
#    main()

base_path = Path.cwd()
test_path = base_path / 'GUI' / 'Testing'
data_path = test_path
results_path = base_path / 'GUI' / 'Output'
icon_path = base_path / 'GUI' / 'icons'
icons = IconPaths(icon_path)

#%% Initial Plan Settings
config_file = 'TestPlanEvaluationConfig.xml'
desc = PlanDescription(Path.cwd(), 'DVH', 'AA, BB', '11', 'LUNR', 'C1',
                        4800, 4,  'Tuesday, August 29, 2017 16:19:54')
report_name = 'SABR 54 in 3'

#%% Load Config file and Report definitions
(config, report_definitions) = initialize(data_path, config_file)
report = deepcopy(report_definitions[report_name])

#%% Load list of Plan Files
plan_list = find_plan_files(config, test_path)
sg.SetOptions(element_padding=(0,0), margins=(0,0))
plan_header = create_plan_header(desc)
report_header = create_report_header(report)
plan_selection = plan_selector(plan_list)
layout = [[plan_header, report_header],
          [plan_selection]
          ]

w = sg.Window('Plan Evaluation',
    layout=layout,
    resizable=True,
    debugger_enabled=True,
    finalize=True,
    element_justification="left")

while True:
    event, values = w.Read(timeout=200)
    if event is None:
        break
    elif event == sg.TIMEOUT_KEY:
        continue