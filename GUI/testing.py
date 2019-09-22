#!/usr/bin/env python
'''Run tests of the GUI interface
'''

#%% imports
import sys
import os
from pathlib import Path
from operator import attrgetter

from typing import Any, Dict, Tuple
from copy import deepcopy
from functools import partial

import xml.etree.ElementTree as ET

import tkinter.filedialog as tkf
import tkinter as tk
from tkinter import messagebox

import PySimpleGUI as sg

import xlwings as xw

from build_plan_report import initialize, read_report_files
from plan_report import Report
from plan_data import DvhFile, Plan

#%% setup functions
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

def build_data_lists(plan, report):
    plan_references = [report_item.reference for report_item in report.report_elements.values()]
    reference_data = [report_item.reference_group() for report_item in plan_references]
    reference_set = sorted(set(reference_data), key=attrgetter('reference_type', 'reference_name'))

    element_names = list()
    for group in plan.data_elements.values():
        plan_items = [item for item in group.keys()]
        element_names.extend(plan_items)
    return (element_names, reference_set)





#%% GUI settings
def run_gui(icon_path, element_names, reference_set):
    match_icon = icon_path / 'Checkmark.png'
    not_matched_icon = icon_path / 'Error_Symbol.png'
    column_names = ['Name', 'Type', 'Laterality', 'Match', 'Matched Item']
    show_column = [False, True, False, False, True]
    menu = ['', ['&Match', [element_names],'&Enter']]
    column_widths = [25, 15, 15, 15, 25]

    treedata = sg.TreeData()
    treedata.Insert('','matched', 'Matched', [], icon=match_icon)
    treedata.Insert('','not_matched', 'Not Matched', [], icon=not_matched_icon)
    for ref in reference_set:
        lat = ref.laterality + ' ' if ref.laterality else ''
        match_name = lat + ref.reference_name
        if ref.match_status:
            treedata.Insert('matched', match_name, ref.reference_name, ref)
        else:
            treedata.Insert('not_matched', match_name, ref.reference_name, ref)
    layout = [[ sg.Text('Report Item Matching') ],
              [ sg.Tree(data=treedata,
                        headings=column_names,
                        visible_column_map=show_column,
                        col0_width=25,
                        col_widths=column_widths,
                        auto_size_columns=True,
                        num_rows=20,
                        key='Match_tree',
                        show_expanded=True,
                        right_click_menu= menu,
                        select_mode='browse',
                        enable_events=False),
                ],
                [ sg.Button('Ok'), sg.Button('Cancel')]
            ]

    window = sg.Window('Match Items', layout=layout, keep_on_top=True,
        resizable=True,  return_keyboard_events=True,  finalize=True)


    while True:     # Event Loop
        event, values = window.Read()
        if event in (None, 'Cancel'):
            break
        print(event, values)


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
    (match, not_matched) = report.match_elements(plan)
    element_names, reference_set = build_data_lists(plan, report)
    run_gui(icon_path, element_names, reference_set)

if __name__ == '__main__':
    main()
