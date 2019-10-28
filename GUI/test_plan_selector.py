'''
Created on Sun Mar 18 21:37:14 2018

@author: Greg
Defines Classes and Methods related to reading plan data and extracting
elements for analysis.
'''


from typing import Union, Tuple, Dict, List, Any
from pathlib import Path
import textwrap as tw
from operator import attrgetter
import xml.etree.ElementTree as ET
import tkinter as tk
import PySimpleGUI as sp

from plan_data2 import get_dvh_list, PlanDescription

Value = Union[int, float, str]
ConversionParameters = Dict[str, Union[str, float, None]]

def load_config(base_path: Path, config_file_name: str)->ET.Element:
    '''Load the XML configuration file
    Arguments:
        base_path {Path} -- The directory containing the config file.
        config_file_name {str} -- The name of configuration file.
    Returns:
        ET.Element -- The root element of the XML config data
    '''
    config_path = base_path / config_file_name
    config_tree = ET.parse(config_path)
    return config_tree.getroot()

def find_plan_files(config, plan_path: Path = None)->List[PlanDescription]:
    '''Load DVH file headers for all .dvh files in a directory.
    If plan_path is not given, the default directory in the config file is used.
    Arguments:
        config {ET.Element} -- An XML element containing default paths.
        plan_path {Path} -- A directory containing .dvh files.
    Returns:
        List[PlanDescription] -- A sorted list containing descriptions of all
            .dvh files identified in plan_path.
    '''
    sort_list = ('patient_name', 'course', 'plan_name', 'export_date')
    plan_list = get_dvh_list(config, plan_path)
    if plan_list:
        plan_set = sorted(plan_list, key=attrgetter(*sort_list))
    return plan_set


def plan_selector(plan_list: List[PlanDescription]):
    '''Summary info for a Plan file.
    Attributes:
        plan_file {Path} -- The full path to the plan file.
        file_type {str} -- The type of plan file. Currently only "DVH".
        patient_name {str} -- The full name of the patient.
        patient_id {str} -- The ID assigned to the patient (CR#).
        plan_name {str} -- The plan ID, or name.
        course {optional, str} -- The course ID.
        dose {optional, float} -- The prescribed dose in cGy.
        fractions {optional, int} -- The number of fractions.
        export_date {optional, str} -- The date, as a string, when the plan
            file was exported.
    '''
    patients = {plan.name_str() for plan in plan_list}
    patient_list = sorted(patients)
    #print(plan_list)
    #print(patient_list)
    # Constants
    column_names = ['Patient', 'Plan Info', 'Course', 'Dose', 'Fractions', 'File', 'Type']
    show_column = [False, True, False, True, False]
    column_widths = [30, 30, 5, 5, 30, 10]
    tree_settings = dict(headings=column_names,
                         visible_column_map=show_column,
                         #col0_width=30,
                         #col_widths=column_widths,
                         auto_size_columns=True,
                         justification='left',
                         num_rows=5,
                         key='Plan_tree',
                         show_expanded=True,
                         select_mode='browse',
                         enable_events=False)
    # Tree data
    # Plan Files for selecting
    treedata = sp.TreeData()
    for patient in patient_list:
        treedata.Insert('', patient, patient, [])
    for plan in plan_list:
        patient = plan.name_str()
        plan_info = plan.plan_str()
        #values_list = [patient, plan_info, plan.course, plan.dose, plan.fractions, plan.plan_file.name, plan.file_type]
        values_list = [plan_info]
        treedata.Insert(patient, plan_info, plan_info, values_list)
    return sp.Tree(data=treedata, **tree_settings)

#%% Load list of Plan Files

base_path = Path.cwd()
test_path = base_path
config_file = 'TestPlanEvaluationConfig.xml'
config = load_config(base_path, config_file)
plan_list = find_plan_files(config, test_path)
#print(plan_list)
ps = plan_selector(plan_list)


w = sp.Window('Plan Evaluation',
    layout=[[ps]],
    default_element_size=(45, 1),
    default_button_element_size=(None, None),
    auto_size_text=True,
    auto_size_buttons=True,
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
    resizable=True,
    disable_close=False,
    disable_minimize=False,
    right_click_menu=None,
    transparent_color=None,
    debugger_enabled=False,
    finalize=True,
    element_justification="left")



while True:
    event, values = w.Read(timeout=200)
