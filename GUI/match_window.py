#!/usr/bin/env python
'''Run tests of the GUI interface
'''

#%% imports etc.
import sys
import os
from pathlib import Path
from operator import attrgetter

from typing import Optional, Union, Any, Dict, Tuple, List, Set
from typing import NamedTuple
from copy import deepcopy
from functools import partial

import xml.etree.ElementTree as ET

import tkinter.filedialog as tkf
import tkinter as tk
from tkinter import messagebox

import PySimpleGUI as sg

import xlwings as xw

from build_plan_report import initialize, read_report_files
from plan_report import Report, ReferenceGroup, MatchList, MatchHistory
from plan_data import DvhFile, Plan, PlanItemLookup, PlanElements
from main_window import IconPaths

Values = Dict[str, List[str]]


#%% Match GUI functions
def plan_item_menu(plan_elements: PlanItemLookup,
                   select_type: str = None)->List[PlanElements]:
    '''Generate a PlanItem Selection menu from a particular type of PlanItem.
    '''
    element_list = sorted(plan_elements.values(), key=attrgetter('name'))
    if select_type:
        element_list = [elmt.name for elmt in element_list
                        if elmt.element_type in select_type]
    else:
        element_list = [elmt.name for elmt in element_list]
    menu = ['', ['&Match', [element_list], 'Enter &Value', '&Clear']]
    return menu


def make_reference_list(reference_data: Dict[str, ReferenceGroup],
              sort_list: List[str] = ['reference_type', 'reference_name']
              )->List[ReferenceGroup]:
    '''Generate a sorted list of Reference matches.
    '''
    reference_list = list(reference_data.values())
    if sort_list:
        reference_set = sorted(reference_list, key=attrgetter(*sort_list))
    else:
        reference_set = reference_list
    return reference_set


def enter_value(reference_name):
    '''Simple pop-up window to enter a text value.
    '''
    title = 'Enter a value for {}.'.format(reference_name)
    layout = [[sg.InputText()], [sg.Ok(), sg.Cancel()]]
    window = sg.Window(title, layout, keep_on_top=True)
    event, values = window.Read()
    window.Close()
    if 'Ok' in event:
        return values[0]
    return None


def update_menu(values: Values, item_menu, item_list: List[str],
                reference_data: Dict[str, ReferenceGroup],
                element_types: Dict[str, str]):
    '''Update the plan item selection
    '''
    selected_item = values['Match_tree'][0]
    ref = reference_data[selected_item]
    selected_type = ref.reference_type
    for index, item_name in enumerate(item_list):
        item_type = element_types[item_name]
        if item_type == selected_type:
            item_menu.entryconfig(index, state='normal')
        else:
            item_menu.entryconfig(index, state='disabled')
    return selected_type

def update_tree(tree: sg.Tree, new_value: ReferenceGroup):
    lookup = new_value.match_name
    tree.Update(key=lookup, value=new_value)


def update_match(event: str, values: Values, tree: sg.Tree,
                 reference_data: Dict[str, ReferenceGroup],
                 history: MatchHistory)->MatchHistory:
    '''Update the reference lists
    '''
    selection = values.get('Match_tree')
    if not selection:
        return history
    ref = reference_data.get(selection[0])
    old_value = ReferenceGroup(*ref)
    new_value = ReferenceGroup(*ref)
    if 'Enter Value' in event:
        item_name = enter_value(ref.reference_name)
        status = 'Direct Entry'
    elif 'Clear' in event:
        item_name = None
        status = None
    else:
        item_name = event
        status = 'Manual'
    new_value = ReferenceGroup(*new_value[0:-2], status, item_name)
    history.add(old_value, new_value)
    update_tree(tree, new_value)
    return (old_value, new_value)


#%% GUI settings
def match_window(icons: IconPaths, plan_elements: PlanItemLookup,
                 reference_data: List[ReferenceGroup])->sg.Window:
    # Constants
    column_names = ['Name', 'Type', 'Laterality', 'Match', 'Matched Item']
    show_column = [False, True, False, False, True]
    column_widths = [30,15,15,15,30]
    menu = plan_item_menu(plan_elements)
    tree_settings = dict(headings=column_names,
                         visible_column_map=show_column,
                         col0_width=30,
                         col_widths=column_widths,
                         auto_size_columns=False,
                         justification='left',
                         num_rows=20,
                         key='Match_tree',
                         show_expanded=True,
                         select_mode='browse',
                         enable_events=True,
                         right_click_menu=menu)
    # Tree data
    reference_set = make_reference_list(reference_data)
    # Plan Items for selecting
    treedata = sg.TreeData()
    treedata.Insert('','matched', 'Matched', [], icon=icons.path('match_icon'))
    treedata.Insert('','not_matched', 'Not Matched', [],
                    icon=icons.path('not_matched_icon'))
    for ref in reference_set:
        name = ref.match_name
        if ref.match_status:
            treedata.Insert('matched', name, name, ref)
        else:
            treedata.Insert('not_matched', name, name, ref)

    # Build window
    layout = [[sg.Text('Report Item Matching')],
              [sg.Tree(data=treedata, **tree_settings)],
              [sg.Button('Approve'), sg.Button('Cancel')]
             ]
    window = sg.Window('Match Items', layout=layout,
                       keep_on_top=True, resizable=True,
                       return_keyboard_events=False,  finalize=True)
    return window

def manual_match(report: Report, plan: Plan, icons: IconPaths)->Tuple[Report, Plan]:
    reference_data = report.get_matches()
    plan_elements = plan.items()
    element_types = {name: elmt.element_type
                     for name, elmt in plan_elements.items()}
    # %% Match Window
    window = match_window(icons, plan_elements, reference_data)
    tree = window['Match_tree']
    tkmenu = tree.TKRightClickMenu # The top-level right-click menu
    menu_id = tkmenu.entrycget('Match','menu').split('.')[-1] # The sub-menu name
    item_menu = tkmenu.children[menu_id] # The sub-menu

    menu_def_list = tree.RightClickMenu
    item_list = menu_def_list[1][tkmenu.index('Match')+1][0] # List of sub-menu items

    history = MatchHistory()
    num_updates = None
    done = False
    event, values = window.Read()
    while not done:
        event, values = window.Read(timeout=200)
        if event is None:
            break
        if event in 'Cancel':
            break
        elif event == sg.TIMEOUT_KEY:
            continue
        elif event in 'Match_tree':
            update_menu(values, item_menu, item_list, reference_data, element_types)
        elif event in 'Approve':
            num_updates = len(history.changed())
            break
        else:
            (old, new) = update_match(event, values, reference_data)
            report.update_ref(new, plan)
            history.add(old, new)
            update_tree(tree, new)
    window.Close()
    return report, num_updates


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
    report.match_elements(plan)
    (report, plan, num_updates) = manual_match(report, plan, icons)


if __name__ == '__main__':
    main()
