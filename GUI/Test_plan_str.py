'''
Created on Sun Mar 18 21:37:14 2018

@author: Greg
Defines Classes and Methods related to reading plan data and extracting
elements for analysis.
'''


from typing import Union, NamedTuple, Tuple, Dict, List, Any
from pathlib import Path
import textwrap as tw
import tkinter as tk
import PySimpleGUI as sp


Value = Union[int, float, str]
ConversionParameters = Dict[str, Union[str, float, None]]


class PlanDescription(NamedTuple):
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
    plan_file: Path
    file_type: str
    patient_name: str
    patient_id: str
    plan_name: str
    course: str = None
    dose: float = None
    fractions: int = None
    export_date: str = None
    
    def parse_name(self):
        '''Patient Name         : AA, BB
        '''
        name = self.patient_name.strip()
        if ',' in name:
            last, first = name.split(',',1)
        elif ' ' in name:
            first, last = name.split(' ',1)
        else:
            last = name
            first = ' '
        return first.strip(), last.strip()

    def __str__(self):
        '''Make a summary string of the plan info.
        '''
        pattern = '{last:>20} {first_ltr} ({ID:0>8}) Plan: {plan:<12} [{exp_date}]'
        first, last = self.parse_name()
        text = pattern.format(last=last, first_ltr=first[0], ID=self.patient_id, plan=self.plan_name, exp_date=self.export_date)
        return text

desc = PlanDescription(Path.cwd(), 'DVH', 'AA, BB', '11', 'LUNR', 'C1', 4800, 4,  'Tuesday, August 29, 2017 16:19:54')

plan_pattern = 'Dose:\t{dose:>4.1f} in {fractions:>2d}\nCourse:\t{course}\nExported:\t{exp_date}'
plan_text = plan_pattern.format(dose=desc.dose, fractions=desc.fractions, course=desc.course, exp_date=desc.export_date)
plan_title = sp.Text(text=desc.plan_name, font=('Calibri', 14, 'bold'), justification='center', key='plan_title', visible=True)
plan_desc = sp.Text(text=plan_text, key='plan_desc', visible=True)

patient_pattern = 'Name:\t{patient_name}\nID:\t{id:0>8}'
patient_text = patient_pattern.format(patient_name=desc.patient_name, id=desc.patient_id)
patient_desc = sp.Text(text=patient_text, key='patient_desc', visible=True)
patient_header = sp.Frame('Patient:', [[patient_desc]],  title_location=sp.TITLE_LOCATION_TOP_LEFT, font=('Calibri', 12), key='patient_header', element_justification='left')

plan_header = sp.Frame('Plan', [[plan_title], [plan_desc], [patient_header]],  title_location=sp.TITLE_LOCATION_TOP, font=('Calibri', 14, 'bold'), key='plan_header', element_justification='center', relief=sp.RELIEF_GROOVE, border_width=5)

report_name =  'SABR Evaluation 48Gy4F'
description = 'SABR Plan Evaluation Sheet for 12Gy/fr Schedules (48 Gy in 4F) or (60Gy/5F)'
wrapped_desc = tw.fill(description, width=40)

data_path = Path.cwd()
file_path = data_path / 'SABR Plan Evaluation Worksheet BLANK For testing.xlsx'
sheet_header = 'WorkSheet:  '
file_header = 'File:\t    '
spacer = '\t    '
file_name = file_path.name
file_lines = tw.wrap(file_name, width=30)
wrapped_file = file_header + file_lines[0] + '\n'
for line in file_lines[1:]:
    wrapped_file += spacer + line +'\n'
wrapped_file = wrapped_file[0:-1]  # remove final newlines
worksheet = 'EvaluationSheet 48Gy4F 60Gy5F'
sheet_lines = tw.wrap(worksheet, width=30)
wrapped_sheet = sheet_header + sheet_lines[0] + '\n'
for line in sheet_lines[1:]:
    wrapped_sheet += spacer + line +'\n'
wrapped_sheet = wrapped_sheet[0:-1] # remove final newlines
template_str = wrapped_file + '\n' + wrapped_sheet

report_title = sp.Text(text=report_name, font=('Calibri', 14, 'bold'), justification='center', key='report_title', visible=True)
report_desc = sp.Text(text=wrapped_desc, key='report_desc', visible=True)
template_desc = sp.Text(text=template_str, key='template_desc', visible=True)

template_header = sp.Frame('Template:', [[template_desc]],  title_location=sp.TITLE_LOCATION_TOP_LEFT, font=('Calibri', 12), key='template_header', element_justification='left')

report_header = sp.Frame('Report', [[report_title],[report_desc],[template_header]],  title_location=sp.TITLE_LOCATION_TOP, font=('Calibri', 14, 'bold'), key='report_header', element_justification='center', relief=sp.RELIEF_GROOVE, border_width=5)

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



w.Read()
