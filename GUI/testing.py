#!/usr/bin/env python
'''Run tests of the GUI interface
'''

#%% imports
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
from plan_report import Report, ReferenceGroup, MatchList
from plan_data import DvhFile, Plan, PlanItemLookup

Values = Dict[str, List[str]]


class HistoryItem(NamedTuple):
    '''Record of a change made to a reference match.
    Attributes:
        old_value {ReferenceGroup} -- The value before the change
        new_value {ReferenceGroup} -- The value after the change
    '''
    old_value: ReferenceGroup
    new_value: ReferenceGroup = None

class History(list):
    '''A record of the changes made to the reference matching.
    Attributes:
        reference_name {str} -- The name of the PlanReference
    '''
    old_value: ReferenceGroup
    new_value: ReferenceGroup = None

    def __init__(self):
        '''Create an empty list
        '''
        super().__init__()

    def add(self, old_value: ReferenceGroup, new_value: ReferenceGroup = None):
        '''Record a new match change.
        Arguments:
            old_value {ReferenceGroup} -- The value before the change
            new_value {ReferenceGroup} -- The value after the change
        '''
        self.append(HistoryItem(old_value, new_value))

    def undo(self)->HistoryItem:
        return self.pop()


#%% setup functions
def match_name(reference: ReferenceGroup)->str:
    '''Form a match name from a reference name and laterality.
    Arguments:
            reference {ReferenceGroup} -- The reference to label.
    Returns:
        str -- A unique name for the reference that includes laterality.
    '''
    if reference.laterality:
        lat = reference.laterality + ' '
    else:
        lat = ''
    name = lat + reference.reference_name
    return name


def sort_dict(dict_data: Dict[str, Any],
              sort_list: List[str] = None
              )->List[ReferenceGroup]:
    '''Generate a sorted list of from dictionary values. sort_list contains
    attributes of the dictionary values.
    '''
    # TODO Add sort_dict to data utilities
    data_list = list(dict_data.values())
    if sort_list:
        data_set = sorted(data_list, key=attrgetter(*sort_list))
    else:
        data_set = data_list
    return data_set


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


def enter_value(reference_name):
    '''Simple pop-up window to enter a text value.
    '''
    title = 'Enter a value for {}.'.format(reference_name)
    layout = [[sg.InputText()], [sg.Ok(), sg.Cancel()]]
    window = sg.Window(title, layout)
    event, values = window.Read()
    window.Close()
    if 'Ok' in event:
        return values[0]
    return None

def update_match(event: str, values: Values,
                 reference_data: Dict[str,ReferenceGroup],
                 tree: sg.Tree,
                 history: History)->Tuple[History, Union[ReferenceGroup, None]]:
    '''Update the reference lists
    '''
    old_value = ReferenceGroup(*reference_data)
    new_value = ReferenceGroup(*reference_data)
    selection = values.get('Match_tree')
    if not selection:
        return history
    plan_item = selection[0]  #do I need this?
    if 'ENTER' in event:
        new_value.plan_Item = enter_value(reference_data.reference_name)
    else:
        plan_item_name = values['Match_tree'][0]
        new_value.plan_Item = plan_item_name
    history.add(old_value, new_value)
    lookup = match_name(new_value)
    # Question use Icon to indicate modified value?
    tree.Update(key=lookup, value=new_value)
    return history


def rerun_match(report: Report, plan: Plan)->Tuple[MatchList, MatchList]:
    '''Re-run the match with updated plan data and then apply stored manual
        matching and entries.
    '''
    # TODO add update match method
    pass


#%% GUI settings
def run_gui(icon_path, plan, report):
    # Constants
    match_icon = icon_path / 'Checkmark.png'
    not_matched_icon = icon_path / 'Error_Symbol.png'
    changed_icon = icon_path / 'emblem-new'
    column_names = ['Name', 'Type', 'Laterality', 'Match', 'Matched Item']
    show_column = [False, True, False, False, True]
    column_widths = [25, 15, 15, 15, 25]
    item_types = plan.types()
    tree_settings = dict(headings=column_names,
                         visible_column_map=show_column,
                         col0_width=30,
                         col_widths=column_widths,
                         auto_size_columns=True,
                         num_rows=20,
                         key='Match_tree',
                         show_expanded=True,
                         select_mode='browse',
                         enable_events=False)
    # Report and Plan data
    reference_data = report.plan_references()
    plan_elements = plan.items()

    # Plan Items for selecting
    element_list = sort_dict(plan_elements, ['element_type', 'name'])
    menu = ['', ['&Match', [element_list],'&ENTER']]
    tree_settings['right_click_menu'] = menu

    # references for tree
    reference_set = sort_dict(reference_data,
                              ['reference_type', 'reference_name'])
    treedata = sg.TreeData()
    treedata.Insert('','matched', 'Matched', [], icon=match_icon)
    treedata.Insert('','not_matched', 'Not Matched', [], icon=not_matched_icon)
    for ref in reference_set:
        name = match_name(ref)
        if ref.match_status:
            treedata.Insert('matched', name, ref.reference_name, ref)
        else:
            treedata.Insert('not_matched', name, ref.reference_name, ref)
    # Build window
    layout = [[sg.Text('Report Item Matching')],
              [sg.Tree(data=treedata, **tree_settings)],
              [sg.Button('Ok'), sg.Button('Cancel')]
             ]
    window = sg.Window('Match Items', layout=layout,
                       keep_on_top=True, resizable=True,
                       return_keyboard_events=False,  finalize=True)

    history = History()
    done = False
    while not done:
        event, values = window.Read()
        if event in (None, 'Cancel', 'Ok'):
            # FIXME run data update ore reset methods
            break
        else:
            history = update_match(event, values, reference_data,
                                   window['Match_tree'], history)
    window.Close()


# %% __rep__ debug
def print_report(report):
    str(report)

#%% Run Tests
def main():
    '''Define Folder Paths, load report and plan data.
    '''
    base_path = Path.cwd()
    test_path = base_path / 'GUI' / 'Testing'
    data_path = base_path / 'Data'
    results_path = base_path / 'GUI' / 'Output'
    icon_path = base_path / 'icons'

    (config, plan, report) = load_test_data(data_path, test_path)
    report.match_elements(plan)
    run_gui(icon_path, plan, report)

if __name__ == '__main__':
    main()
