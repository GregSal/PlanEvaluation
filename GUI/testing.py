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
reference_data = [report_item.reference_group() for report_item in plan_references]
reference_set = set(reference_data)
# TODO Sort reference_set

#%% plan elements
element_names = list()
for group in plan.data_elements.values():
    plan_items = [item for item in group.keys()]
    element_names.extend(plan_items)

#%% icons
match_icon = icon_path  /  'Checkmark.png'
not_matched_icon = icon_path  /  'Error_Symbol.png'
#Info_Light
#Target
#Chart_Graph_Ascending

#%% Matching GUI

treedata = sg.TreeData()
treedata.Insert('','matched', 'Matched', [], icon=match_icon)
treedata.Insert('','not_matched', 'Not Matched', [], icon=not_matched_icon)
for reference in reference_set:
    lat = reference.laterality + ' ' if reference.laterality else ''
    match_name = lat + reference.reference_name
    if reference.match_status:
        treedata.Insert('matched',match_name, reference.reference_name, reference)
    else:
        treedata.Insert('not_matched',match_name, reference.reference_name, reference)
# TODO Control which items are displayed
# TODO add method to select plan item
# TODO add method to manually enter value
layout = [[ sg.Text('Report Item Matching') ],
          [ sg.Tree(data=treedata,
                    headings=['Name', 'Type', 'Laterality', 'Match', 'Matched Item'],
                    auto_size_columns=True,
                    num_rows=20,
                    key='_TREE_',
                    show_expanded=True,
                    enable_events=True),
            ],
          [ sg.Button('Ok'), sg.Button('Cancel')]]

#TODO Allow window to resize
window = sg.Window('Match Items').Layout(layout)


while True:     # Event Loop
    event, values = window.Read()
    if event in (None, 'Cancel'):
        break
    print(event, values)


# %% __rep__ debug
str(report)

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


#%% Demo GUI
# Base64 versions of images of a folder and a file. PNG files (may not work with PySimpleGUI27, swap with GIFs)

folder_icon = b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsSAAALEgHS3X78AAABnUlEQVQ4y8WSv2rUQRSFv7vZgJFFsQg2EkWb4AvEJ8hqKVilSmFn3iNvIAp21oIW9haihBRKiqwElMVsIJjNrprsOr/5dyzml3UhEQIWHhjmcpn7zblw4B9lJ8Xag9mlmQb3AJzX3tOX8Tngzg349q7t5xcfzpKGhOFHnjx+9qLTzW8wsmFTL2Gzk7Y2O/k9kCbtwUZbV+Zvo8Md3PALrjoiqsKSR9ljpAJpwOsNtlfXfRvoNU8Arr/NsVo0ry5z4dZN5hoGqEzYDChBOoKwS/vSq0XW3y5NAI/uN1cvLqzQur4MCpBGEEd1PQDfQ74HYR+LfeQOAOYAmgAmbly+dgfid5CHPIKqC74L8RDyGPIYy7+QQjFWa7ICsQ8SpB/IfcJSDVMAJUwJkYDMNOEPIBxA/gnuMyYPijXAI3lMse7FGnIKsIuqrxgRSeXOoYZUCI8pIKW/OHA7kD2YYcpAKgM5ABXk4qSsdJaDOMCsgTIYAlL5TQFTyUIZDmev0N/bnwqnylEBQS45UKnHx/lUlFvA3fo+jwR8ALb47/oNma38cuqiJ9AAAAAASUVORK5CYII='

file_icon = b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsSAAALEgHS3X78AAABU0lEQVQ4y52TzStEURiHn/ecc6XG54JSdlMkNhYWsiILS0lsJaUsLW2Mv8CfIDtr2VtbY4GUEvmIZnKbZsY977Uwt2HcyW1+dTZvt6fn9557BGB+aaNQKBR2ifkbgWR+cX13ubO1svz++niVTA1ArDHDg91UahHFsMxbKWycYsjze4muTsP64vT43v7hSf/A0FgdjQPQWAmco68nB+T+SFSqNUQgcIbN1bn8Z3RwvL22MAvcu8TACFgrpMVZ4aUYcn77BMDkxGgemAGOHIBXxRjBWZMKoCPA2h6qEUSRR2MF6GxUUMUaIUgBCNTnAcm3H2G5YQfgvccYIXAtDH7FoKq/AaqKlbrBj2trFVXfBPAea4SOIIsBeN9kkCwxsNkAqRWy7+B7Z00G3xVc2wZeMSI4S7sVYkSk5Z/4PyBWROqvox3A28PN2cjUwinQC9QyckKALxj4kv2auK0xAAAAAElFTkSuQmCC'

#starting_path = sg.PopupGetFolder('Folder to display')
starting_path = str(test_path)
if not starting_path:
    sys.exit()

treedata = sg.TreeData()

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
