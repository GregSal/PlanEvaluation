#!/usr/bin/env python
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



def create_plan_header(desc: PlanDescription)->sp.Frame:
    def format_plan_text(desc: PlanDescription)->sp.Text:
        '''Create a text GUI element containing plan info.
        Arguments:
            desc {PlanDescription} -- Summary data for the plan.
        Returns:
            sp.Text -- A text GUI element with Dose, Course and export date for
                the plan.
        '''
        plan_pattern = 'Dose:\t{dose:>4.1f} in {fractions:>2d}\n'
        plan_pattern += 'Course:\t{course}\n'
        plan_pattern += 'Exported:\t{exp_date}'
        plan_text = plan_pattern.format(dose=desc.dose,
                                        fractions=desc.fractions,
                                        course=desc.course,
                                        exp_date=desc.export_date)
        plan_desc = sp.Text(text=plan_text,
                            key='plan_desc',
                            visible=True)
        return plan_desc

    def format_patient_text(desc: PlanDescription)->sp.Frame:
        '''Create a Frame GUI element containing patient info for the given plan.
        Arguments:
            desc {PlanDescription} -- Summary data for the plan.
        Returns:
            sp.Frame -- A text GUI element with patient name and ID for the plan.
        '''
        patient_pattern = 'Name:\t{patient_name}\n'
        patient_pattern += 'ID:\t{id:0>8n}'
        patient_text = patient_pattern.format(patient_name=desc.patient_name,
                                              id=desc.patient_id)
        patient_desc = sp.Text(text=patient_text,
                               key='patient_desc',
                               visible=True)
        patient_header = sp.Frame('Patient:', [[patient_desc]],
                                  key='patient_header',
                                  title_location=sp.TITLE_LOCATION_TOP_LEFT,
                                  font=('Calibri', 12),
                                  element_justification='left')
        return patient_header

    plan_title = sp.Text(text=desc.plan_name,
                         key='plan_title',
                         font=('Calibri', 14, 'bold'),
                         justification='center', visible=True)
    plan_desc = format_plan_text(desc)
    patient_header = format_patient_text(desc)
    plan_header = sp.Frame('Plan', [[plan_title], [plan_desc], [patient_header]],
                           key='plan_header',
                           title_location=sp.TITLE_LOCATION_TOP,
                           font=('Calibri', 14, 'bold'),
                           element_justification='center',
                           relief=sp.RELIEF_GROOVE, border_width=5)
    return plan_header


def create_report_header(report: Report)->sp.Frame:

    def create_template_header(report: Report)->sp.Frame:
        def wrapped_descriptor(desc_text, header_text,
                               spacer='\t    ', text_width=30):
            lines = tw.wrap(desc_text, width=text_width)
            wrapped_text = header + lines[0] + '\n'
            for line in lines[1:]:
                wrapped_text += spacer + line +'\n'
            wrapped_text = wrapped_text[0:-1] # remove final newlines
            return wrapped_text

        wrapped_file = wrapped_descriptor(report.template_file.name,
                                          'File:\t    ')
        wrapped_sheet = wrapped_descriptor(report.worksheet, 'WorkSheet:  ')
        template_str = wrapped_file + '\n' + wrapped_sheet
        template_desc = sp.Text(text=template_str,
                                key='template_desc',
                                visible=True)
        template_header = sp.Frame('Template:', [[template_desc]],
                                   key='template_header',
                                   title_location=sp.TITLE_LOCATION_TOP_LEFT,
                                   font=('Calibri', 12),
                                   element_justification='left')
        return template_header

    template_header = create_template_header(report)
    wrapped_desc = tw.fill(report.description, width=40)
    report_title = sp.Text(text=report.name,
                           key='report_title',
                           font=('Calibri', 14, 'bold'),
                           justification='center',
                           visible=True)
    report_desc = sp.Text(text=wrapped_desc,
                          key='report_desc',
                          visible=True)
    report_header = sp.Frame('Report', [[report_title],
                                        [report_desc],
                                        [template_header]],
                             key='report_header',
                             title_location=sp.TITLE_LOCATION_TOP,
                             font=('Calibri', 14, 'bold'),
                             element_justification='center',
                             relief=sp.RELIEF_GROOVE, border_width=5)
    return report_header


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
                         col0_width=30,
                         col_widths=column_widths,
                         auto_size_columns=False,
                         justification='left',
                         num_rows=5,
                         key='Plan_tree',
                         show_expanded=True,
                         select_mode='browse',
                         enable_events=True)
    # Tree data
    # Plan Files for selecting
    treedata = sp.TreeData()
    for patient in patient_list:
        treedata.Insert('', patient, patient, [])
    for plan in plan_list:
        patient = plan.name_str()
        plan_info = plan.plan_str()
        values_list = [patient, plan_info, plan.course, plan.dose, plan.fractions, plan.file.name, plan.file_type]
        treedata.Insert(patient, plan_info, plan_info, values_list)
    return sp.Tree(data=treedata, **tree_settings)




#%% GUI settings
def main_window(icons: IconPaths, plan_elements: PlanItemLookup,
                 reference_data: List[ReferenceGroup])->sg.Window:
    plan_header = create_plan_header(desc)
    report_header = create_report_header(report)
    w = sp.Window('Plan Evaluation',
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



#%% Run Tests
def load_test_data(data_path: Path,
                   test_path: Path)->Tuple[ET.Element, Plan, Report]:
    ''' Load test data.
    '''
    # Define Folder Paths
    dvh_file = 'SABR1.dvh'
    report_name = 'SABR 54 in 3'
    config_file = 'PlanEvaluationConfig.xml'
    dvh_path = test_path / dvh_file
    # Load Config file and Report definitions
    (config, report_parameters) = initialize(data_path, config_file)
    report_definitions = read_report_files(**report_parameters)
    report = deepcopy(report_definitions[report_name])
    plan = Plan(config, 'test', DvhFile(dvh_path))
    return(config, plan, report)


def main():
    '''Define Folder Paths, load report and plan data.
    '''
    base_path = Path.cwd()
    test_path = base_path / 'GUI' / 'Testing'
    data_path = base_path / 'Data'
    results_path = base_path / 'GUI' / 'Output'
    icon_path = base_path / 'icons'
    icons = IconPaths(icon_path)

    (config, plan, report) = load_test_data(data_path, test_path)
    w.Read()

    report.match_elements(plan)
    (report, plan, num_updates) = manual_match(report, plan, icons)


if __name__ == '__main__':
    main()
