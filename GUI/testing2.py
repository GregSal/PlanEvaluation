#!/usr/bin/env python
'''Run tests of the GUI interface
'''
#%% imports
import sys
import os

from typing import Any, Dict, Tuple
from copy import deepcopy
from pathlib import Path
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

#%% setup
def load_test_data(data_path: Path,
                   test_path: Path)->Tuple[ET.Element, Plan, Report]:
    ''' Load test data.
    '''
    #%% Define Folder Paths
    dvh_file = 'SABR1.dvh'
    report_name = 'SABR 54 in 3'
    config_file = 'PlanEvaluationConfig.xml'
    dvh_path = test_path / dvh_file

    #%% Load Config file and Report definitions
    (config, report_parameters) = initialize(data_path, config_file)
    report_definitions = read_report_files(**report_parameters)
    report = deepcopy(report_definitions[report_name])
    plan = Plan(config, 'test', DvhFile(dvh_path))
    return(config, plan, report)




#%% Run Tests
def main():
    ''' Load test data and run selected tests
    '''
    #%% Define Folder Paths
    base_path = Path.cwd()
    test_path = base_path / 'Testing'
    data_path = base_path / 'Data'
    results_path = base_path / 'Output'

    (config, plan,report) = load_test_data(data_path, test_path)
    (match, not_matched) = report.match_elements(plan)

#if __name__ == '__main__':
#    main()

#%% Define Folder Paths
base_path = Path.cwd()
test_path = base_path / 'GUI' / 'Testing'

data_path = base_path / 'Data'
results_path = base_path / 'GUI' / 'Output'
icon_path = base_path / 'icons'

#%% load data
(config, plan, report) = load_test_data(data_path, test_path)
(match, not_matched) = report.match_elements(plan)

#%% load data
plan_references = [report_item.reference for report_item in report.report_elements.values()]
tree_data = [report_item.reference_group() for report_item in plan_references]
plan_items = [item.name for item in plan.plan_items]
print(tree_data)

# %% __rep__ debug
str(report)

match_icon = icon_path  /  'Checkmark.png'
not_matched_icon = icon_path  /  'Error_Symbol'
#Info_Light
#Target
#Chart_Graph_Ascending

#%% Matching GUI

treedata = sg.TreeData()
treedata.Insert('','Matched',icon=match_icon)
treedata.Insert('','Not Matched',icon=not_matched_icon)

#%% Demo GUI
#starting_path = sg.PopupGetFolder('Folder to display')
starting_path = str(test_path)
if not starting_path:
    sys.exit()

def add_files_in_folder(parent, dirname):
    files = os.listdir(dirname)
    for f in files:
        fullname = os.path.join(dirname,f)
        if os.path.isdir(fullname):            # if it's a folder, add folder and recurse
            treedata.Insert(parent, fullname, f, values=[], icon=folder_icon)
            add_files_in_folder(fullname, fullname)
        else:

            treedata.Insert(parent, fullname, f, values=[os.stat(fullname).st_size], icon=file_icon)

add_files_in_folder('', starting_path)

layout = [[ sg.Text('File and folder browser Test') ],
          [ sg.Tree(data=treedata,
                    headings=['Size', ],
                    auto_size_columns=True,
                    num_rows=20,
                    col0_width=30,
                    key='_TREE_',
                    show_expanded=True,
                    enable_events=True),
            ],
          [ sg.Button('Ok'), sg.Button('Cancel')]]

window = sg.Window('Tree Element Test').Layout(layout)


while True:     # Event Loop
    event, values = window.Read()
    if event in (None, 'Cancel'):
        break
    print(event, values)
