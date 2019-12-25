#!/usr/bin/env python
'''Run tests of the GUI interface
'''

#%% imports etc.
from pathlib import Path
from operator import attrgetter
from copy import deepcopy
from typing import Dict, Tuple, List
import xml.etree.ElementTree as ET
import PySimpleGUI as sg
from build_plan_report import load_config, load_reports, IconPaths, load_dvh
from plan_report import Report, ReferenceGroup, MatchHistory
from plan_data import get_laterality_exceptions, find_plan_files
from plan_data import Plan, PlanItemLookup, PlanElements, get_default_units
from gui_helper import ColumnSettings, ColumConfig, MenuDict, TreeRtClick


Values = Dict[str, List[str]]

##%% Menu Definitions
def item_menu(plan_elements: PlanItemLookup,
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


def item_group(plan_elements: PlanItemLookup)->Dict[str, List[PlanElements]]:
    '''Generate PlanItem Selection menus for all types of PlanItems.
    '''
    itypes = {elmt.element_type for elmt in plan_elements.values()}
    group = {itype: item_menu(plan_elements, itype) for itype in itypes}
    return group


def menu_options(plan_elements: PlanItemLookup)->MenuDict:
    '''Build a group of invisible ButtonMenus that provide multiple
    right-click menu options.
    '''
    default_menu = item_menu(plan_elements)
    item_group_dict = item_group(plan_elements)
    menu_dict = MenuDict(**item_group_dict, default=default_menu)
    return menu_dict

#%% Data for Tree
def make_reference_list(reference_data: Dict[Tuple[str], ReferenceGroup],
              sort_list: List[str] = None)->List[ReferenceGroup]:
    '''Generate a sorted list of Reference matches.
    Arguments:
        reference_data {Dict[Tuple[str], ReferenceGroup} -- The Report
            references to the plan.
        sort_list {List[str]} ReferenceGroup attribute names to sort by.
            default sorting is ['reference_type', 'reference_name'].

    '''
    if not sort_list:
        sort_list = ['reference_type', 'reference_name']
    reference_list = list(reference_data.values())
    if sort_list:
        reference_set = sorted(reference_list, key=attrgetter(*sort_list))
    else:
        reference_set = reference_list
    return reference_set

def build_tree_data(reference_data: Dict[Tuple[str], ReferenceGroup],
                    icons: IconPaths,
                    sort_list: List[str] = None
                    )->sg.TreeData:
    '''Assemble the reference data into a tree format, grouping by matched
    status.
    Arguments:
        reference_data {Dict[Tuple[str], ReferenceGroup} -- The Report
            references to the plan.
        sort_list {List[str]} ReferenceGroup attribute names to sort by.
            default sorting is ['reference_type', 'reference_name'].
        icons {IconPaths} -- Path to the icon files to be used for the Matched
            and Not Matched headers
    Returns:
        sg.TreeData The tree data to be passed to the sg.Tree widget.
    '''
    reference_set = make_reference_list(reference_data, sort_list)
    # Plan Items for selecting
    treedata = sg.TreeData()
    treedata.Insert('','matched', 'Matched', [],
                    icon=icons.path('match_icon'))
    treedata.Insert('','not_matched', 'Not Matched', [],
                    icon=icons.path('not_matched_icon'))
    for ref in reference_set:
        idx = ref.reference_index
        name = ref.match_name
        if ref.match_status:
            treedata.Insert('matched', idx, name, ref)
        else:
            treedata.Insert('not_matched', idx, name, ref)
    return treedata

#%% Matching actions
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

def update_match(event: str, selection: str, tree: sg.Tree,
                 reference_data: Dict[str, ReferenceGroup],
                 history: MatchHistory)->MatchHistory:
    '''Update the reference lists
    '''
    ref = reference_data.get(selection)
    if ref:
        old_value = ReferenceGroup(*ref)
        if 'Enter Value' in event:
            item_name = enter_value(ref.reference_name)
            status = 'Direct Entry'
        elif 'Clear' in event:
            item_name = None
            status = None
        else:
            item_name = event
            status = 'Manual'
        new_value = ReferenceGroup(*old_value[0:-2], status, item_name)
        history.add(old_value, new_value)
        tree.update_value(new_value)
    return history


#%% GUI settings
def match_window(icons: IconPaths, plan_elements: PlanItemLookup,
                 reference_data: Dict[Tuple[str], ReferenceGroup])->sg.Window:
    # Tree Settings
    columns = ColumConfig([
        ColumnSettings('col0', 30),
        ColumnSettings('Index', 30, True),
        ColumnSettings('Name',30, False),
        ColumnSettings('Type', 15, True),
        ColumnSettings('Laterality', 15, False),
        ColumnSettings('Match', 15, False),
        ColumnSettings('Matched Item', 30, True)
        ])
    tree_config = columns.column_kwargs(
        num_rows=20,
        show_expanded=True,
        justification='left',
        auto_size_columns=False,
        select_mode='browse',
        enable_events=True
        )
    # Report References as Tree data
    treedata = build_tree_data(reference_data, icons)
    # Plan Items for selecting as right-click menus
    plan_menu_dict = menu_options(plan_elements)
    # Build window
    layout = [[sg.Text('Report Item Matching')],
              [TreeRtClick(
                  key='Match_tree',
                  right_click_menu=plan_menu_dict.default_menu,
                  menu_dict=plan_menu_dict,
                  data=treedata,
                  **tree_config)],
              [sg.Button('Approve'), sg.Button('Cancel')]
             ]
    window = sg.Window('Match Items', layout=layout,
                       keep_on_top=True, resizable=True,
                       return_keyboard_events=False,  finalize=True)
    return window

def manual_match(report: Report, plan: Plan, icons: IconPaths)->Report:
    reference_data = report.get_matches()
    plan_elements = plan.items()
    element_types = {name: elmt.element_type
                     for name, elmt in plan_elements.items()}
    # %% Match Window
    window = match_window(icons, plan_elements, reference_data)

    tree = window['Match_tree']
    tkmenu = tree.TKRightClickMenu # The top-level right-click menu
    menu_id = tkmenu.entrycget('Match','menu').split('.')[-1] # The sub-menu name
    #item_menu = tkmenu.children[menu_id] # The sub-menu

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
        elif event in 'Approve':
            for new_match in history.changed():
                report.update_ref(new_match, plan)
            #num_updates = len(history.changed())
            break
        else:
            selection = values.get('Match_tree')
            if selection:
                history = update_match(event, selection[0], tree,
                                       reference_data, history)
    window.Close()
    return report


#%% Run Tests
def load_test_data(data_path: Path,
                   test_path: Path)->Tuple[ET.Element, Plan, Report]:
    ''' Load test data.
    '''
    # Define Folder Paths
    # Load Config file and Report definitions
    config_file = 'TestPlanEvaluationConfig.xml'
    config = load_config(data_path, config_file)
    code_exceptions_def = config.find('LateralityCodeExceptions')
    # Load Report definitions
    report_name = 'SABR 54 in 3'
    report_definitions = load_reports(config)
    report = deepcopy(report_definitions[report_name])
    # Load DVH plan
    plan_id = 'Plan: LUNR         [June-07-2019 13:50:12]'
    #dvh_file = 'SABR1.dvh'
    plan_parameters = dict(
        default_units=get_default_units(config),
        laterality_exceptions=get_laterality_exceptions(code_exceptions_def),
        name='Plan'
        )
    plan_dict = find_plan_files(config, test_path)
    selected_plan_desc = plan_dict[plan_id]
    plan = load_dvh(selected_plan_desc, **plan_parameters)
    return(config, plan, report)


def main():
    '''Define Folder Paths, load report and plan data.
    '''
    base_path = Path.cwd()
    test_path = base_path / 'GUI' / 'Testing'
    data_path = test_path
    dvh_path = test_path
    results_path = base_path / 'GUI' / 'Output'
    code_path = Path.cwd()
    icon_path = code_path / 'icons'
    icons = IconPaths(icon_path)

    (config, plan, report) = load_test_data(data_path, test_path)
    report.match_elements(plan)
    report = manual_match(report, plan, icons)


if __name__ == '__main__':
    main()
