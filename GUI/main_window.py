'''Run tests of the GUI interface
'''

#%% imports etc.
import os
import sys
import textwrap as tw
from pathlib import Path
from copy import deepcopy
from functools import partial
from operator import attrgetter
import xml.etree.ElementTree as ET
from collections import OrderedDict
from typing import Optional, Union, Any, Dict, Tuple, List, Set, NamedTuple

import xlwings as xw
import PySimpleGUI as sg

from build_plan_report import load_config, update_reports, load_reports, find_plan_files, run_report
from plan_report import Report, ReferenceGroup, MatchList, MatchHistory, rerun_matching
from plan_data import DvhFile, Plan, PlanItemLookup, PlanElements, scan_for_dvh, PlanDescription, get_default_units, get_laterality_exceptions

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
def create_plan_header()->sg.Frame:
    '''Create a Frame GUI element containing patient and plan info.
    Returns:
        sg.Frame -- A group of text GUI s with Dose, Course,
        export date, patient name and ID for the plan.
    '''
    def build_patient_header():
        # Set Patient Label
        pt_name_label = sg.Text('Name:', size=(6,1))
        pt_name_text = sg.Text('', key='pt_name_text', size=(20,1))
        pt_id_label = sg.Text('ID:', size=(6,1))
        pt_id_text = sg.Text('', key='id_text', size=(20,1))
        patient_desc = [[pt_name_label, pt_name_text],
                        [pt_id_label, pt_id_text]]
        patient_header = sg.Frame('Patient:', patient_desc,
                                  key='patient_header',
                                  title_location=sg.TITLE_LOCATION_TOP_LEFT,
                                  font=('Calibri', 12),
                                  element_justification='left')
        return patient_header

    def build_plan_info_layout():
        dose_label = sg.Text('Dose:', size=(6,1))
        dose_text = sg.Text('', key='dose_text', size=(30,1))
        course_label = sg.Text('Course:', size=(6,1))
        course_text = sg.Text('', key='course_text', size=(30,1))
        exported_label = sg.Text('Exported:', size=(6,1))
        exported_text = sg.Text('', key='exported_text', size=(30,1))
        plan_header_layout = [[dose_label, dose_text],
                              [course_label, course_text],
                              [exported_label, exported_text]]
        return plan_header_layout

    # Set Main Label
    plan_title = sg.Text(text='', key='plan_title', size=(12,1),
                         font=('Calibri', 14, 'bold'), pad=((5, 0), (5, 10)),                         
                         justification='center')
    load_plan_button = sg.Button(key='load_plan', button_text='Select a Plan',
                                 disabled=True, button_color=('red', 'white'),
                                 border_width=5, pad=((10, 0), (0, 0)),
                                 size=(12, 1), auto_size_button=False,
                                 font=('Times New Roman', 12, 'normal'))
    header_layout = [[plan_title, load_plan_button]]
    header_layout += build_plan_info_layout()
    header_layout += [[build_patient_header()]]
    plan_header = sg.Frame('Plan', header_layout, key='plan_header',
                           font=('Arial Black', 14, 'bold'),
                           element_justification='center',
                           title_location=sg.TITLE_LOCATION_TOP,
                           relief=sg.RELIEF_GROOVE, border_width=5,
                           visible=True)
    return plan_header

def update_plan_header(window: sg.Window, desc: PlanDescription):
    '''Update the text values for the patient and plan info.
    Arguments:
        desc {PlanDescription} -- Summary data for the plan.
        window {} -- The GUI window containing the text.
    '''
    dose_text = desc.format_dose()
    id_text = desc.format_id()
    window['plan_title'].update(value=desc.plan_name)
    window['exported_text'].update(value=desc.export_date)
    window['course_text'].update(value=desc.course)
    window['dose_text'].update(value=dose_text)
    window['pt_name_text'].update(value=desc.patient_name)
    window['id_text'].update(value=id_text)


def plan_selector(plan_dict: OrderedDict):
    '''Plan Selection GUI
    '''
    patients = {plan.name_str() for plan in plan_dict.values()}
    patient_list = sorted(patients)
    column_settings = [
        ('File', False, 30),
        ('Type', False, 6),
        ('Patient Name', False, 12),
        ('Patient ID', False, 10),
        ('Plan Name', False, 6),
        ('Course', False, 5),
        ('Dose', True, 5),
        ('Fractions', False, 3),
        ('Exported On', True, 25)
        ]
    column_names = [col[0] for col in column_settings]
    show_column = [col[1] for col in column_settings]
    column_widths = [col[2] for col in column_settings]
    tree_settings = dict(key='Plan_tree',
                         headings=column_names,
                         visible_column_map=show_column,
                         col0_width=12,
                         col_widths=column_widths,
                         auto_size_columns=False,
                         justification='left',
                         num_rows=5,
                         font=('Verdana', 8, 'normal'),
                         show_expanded=True,
                         select_mode='browse',
                         enable_events=True)
    treedata = sg.TreeData()
    for patient in patient_list:
        treedata.Insert('', patient, patient, [])
    for plan_info, plan in plan_dict.items():
        patient = plan.name_str()
        treedata.Insert(patient, plan_info, plan.plan_name, plan)
    return sg.Tree(data=treedata, **tree_settings)


#%% Report Header
def create_report_header()->sg.Frame:
    template_layout = [
        [sg.Text('File:', size=(10,1)),
         sg.Text('', key='template_file', pad=(0, 5), size=(25,2))],
        [sg.Text('WorkSheet:', size=(10,1)),
         sg.Text('', key='template_sheet', pad=(0, 5), size=(25,1))],
        ]
    report_title = sg.Text(text='',
                           key='report_title',
                           font=('Calibri', 14, 'bold'),
                           size=(12,1),
                           pad=((0, 0), (4, 5)),
                           justification='center',
                           visible=True)
    report_desc = sg.Text(text='',
                          key='report_desc',
                          size=(30,2),
                          pad=((15, 0), (0, 20)),
                          visible=True)
    template_header = sg.Frame('Template:', template_layout,
                                   key='template_header',
                                   title_location=sg.TITLE_LOCATION_TOP_LEFT,
                                   font=('Calibri', 12),
                                   pad=(0, 0),
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


def update_report_header(window: sg.Window, report: Report):
    '''Update the text values for the report header.
    Arguments:
        window {} -- The GUI window containing the text.
        report {Report} -- The selected report.
    '''
    wrapped_desc = tw.fill(report.description, width=40)
    wrapped_file = tw.fill(report.template_file.name, width=30)
    wrapped_sheet = tw.fill(report.worksheet, width=30)
    window['report_title'].update(value=report.name)
    window['report_desc'].update(value=wrapped_desc)
    window['template_file'].update(value=wrapped_file)
    window['template_sheet'].update(value=wrapped_sheet)


#%% Actions
def make_actions_column(report_definitions: Dict[str, Report]):
    '''Report Selection GUI    
    '''
    report_list = ['Select a Report']
    report_list += [str(ky) for ky in report_definitions.keys()]
    report_selector_box = sg.Combo(report_list,
                                    key='report_selector',
                                    pad=((10,10), (20,10)), size=(15, 2),
                                    enable_events=True,
                                    readonly=True)
    match_structures_button = sg.Button(key='match_structures',
                                        button_text='Match Structures',
                                        disabled=True,
                                        button_color=('red', 'white'),
                                        border_width=5, pad=(5, 5),
                                        size=(15, 1), auto_size_button=False,
                                        font=('Times New Roman', 12, 'normal'))
    generate_report_button = sg.Button(key='generate_report',
                                       button_text='Show Report',
                                       disabled=True,
                                       button_color=('red', 'white'),
                                       border_width=5, pad=(5, 5),
                                       size=(15, 1), auto_size_button=False,
                                       font=('Times New Roman', 12, 'normal'))
    actions = sg.Column([[report_selector_box],
                         [match_structures_button],
                         [generate_report_button]
                         ])
    return actions

def select_report(selected_report: str):
    selected_report = values['report_selector']
    report = deepcopy(report_definitions.get(selected_report))
    return report

def load_plan(plan_desc: PlanDescription, **plan_parameters)->Plan:
    '''Load plan data from the specified file or folder.
    Arguments:
        config {ET.Element} -- An XML element containing default paths.
        dvh_loc {DvhSource} -- A DvhFile object, the path, to a .dvh file,
            the name of a .dvh file in the default DVH directory, or a
            directory containing .dvh files. If not given,
            the default DVH directory in config will be used.
    Returns:
        Plan -- The requested or the default plan.
    '''
    plan_file = plan_desc.plan_file
    dvh_file = DvhFile(plan_file)
    plan = Plan(dvh_data=dvh_file, **plan_parameters)
    return plan

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

    # Initial Plan and Report Settings
    config_file = 'TestPlanEvaluationConfig.xml'
    desc = PlanDescription(Path.cwd(), 'DVH', 'AA, BB', '11', 'LUNR', 'C1',
                           4800, 4,  'Tuesday, August 29, 2017 16:19:54')
    report_name = 'SABR 54 in 3'
    report_description = 'SABR Plan Evaluation Sheet for 12Gy/fr Schedules '
    report_description += '(48 Gy in 4F) or (60Gy/5F)'

    # Load Config file and Report definitions
    (config, report_parameters) = initialize(data_path, config_file)
    report_definitions = read_report_files(**report_parameters)
    report = deepcopy(report_definitions[report_name])

    # Load list of Plan Files
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

#%% Load Config file and Report definitions
config_file = 'TestPlanEvaluationConfig.xml'
config = load_config(data_path, config_file)
report_definitions = update_reports(config)
plan_dict = find_plan_files(config, test_path)

code_exceptions_def = config.find('LateralityCodeExceptions')
plan_parameters = dict(
    default_units=get_default_units(config),
    laterality_exceptions=get_laterality_exceptions(code_exceptions_def),
    name='Plan'
    )


#%% Initial Plan Settings
class GuiData():
    '''Parameters used by the GUI interface.
    Attributes:
        selected_plan_desc {PlanDescription} -- The string summary fields for the selected plan.
            Intially = None
        active_plan {Plan} -- The loaded plan. should match with selected_plan_desc.
            Intially = None
        selected_report {Report} -- A deep copy of the report selected from the report definitions.
            Intially = None
        history {MatchHistory} -- A record of all manual matched made and modified this session.
            Initially an empty MatchHistory List.
    '''
    selected_plan_desc: PlanDescription = None
    active_plan: Plan = None
    selected_report: Report = None
    history: MatchHistory = MatchHistory()

data = GuiData()

# Plan Status  Text Colour disabled
load_plan_config = {
    None:       dict(button_text='Select Plan',
                     button_color=('red', 'white'),
                     disabled=True),
    'Selected': dict(button_text='Load Plan',
                     button_color=('black', 'blue'),
                     disabled=False),
    'Loading':  dict(button_text='Loading ...',
                     button_color=('red', 'yellow'),
                     disabled=True),
    'Loaded':   dict(button_text='Plan Loaded',
                     button_color=('black', 'green'),
                     disabled=False)
    }
match_config = {
    None:       dict(button_text='Select Report',
                     button_color=('red', 'white'),
                     disabled=True),
    'Selected': dict(button_text='Match Structures',
                     button_color=('black', 'blue'),
                     disabled=False),
    'Matching': dict(button_text='Matching ...',
                     button_color=('red', 'yellow'),
                     disabled=True),
    'Matched':  dict(button_text='Structured Matched',
                     button_color=('black', 'green'),
                     disabled=False)
    }
generate_config = {
    None:       dict(button_text='',
                     button_color=('red', 'white'),
                     disabled=True),
    'Matched': dict(button_text='Generate Report',
                     button_color=('black', 'blue'),
                     disabled=False),
    'Generating': dict(button_text='Generating Report ...',
                     button_color=('red', 'yellow'),
                     disabled=True),
    'Generated':  dict(button_text='Report Generated',
                     button_color=('black', 'green'),
                     disabled=False)
    }

#%% Create Main Window
sg.SetOptions(element_padding=(0,0), margins=(0,0))
plan_header = create_plan_header()
report_header = create_report_header()
plan_selection = plan_selector(plan_dict)
report_actions = make_actions_column(report_definitions)
layout = [[plan_header, report_header, report_actions],
          [plan_selection]]

window = sg.Window('Plan Evaluation',
                   layout=layout,
                   resizable=True,
                   debugger_enabled=True,
                   finalize=True,
                   element_justification="left")

while True:
    event, values = window.Read(timeout=2000)
    if event is None:
        break
    elif event == sg.TIMEOUT_KEY:
        continue
    elif event in 'Plan_tree':
        plan_desc = values['Plan_tree'][0]
        data.selected_plan_desc = plan_dict.get(plan_desc)
        if data.selected_plan_desc:
            update_plan_header(window, data.selected_plan_desc)
    elif event in 'report_selector':
        data.selected_report = values['report_selector']
        report = select_report(data.selected_report)
        if report:
            update_report_header(window, report)
    elif event in 'load_plan':
        active_plan = load_plan(data.selected_plan_desc, **plan_parameters)
    elif event in 'match_structures':
        rerun_matching(report, active_plan, history)
    elif event in 'generate_report':
        run_report(active_plan, report)
