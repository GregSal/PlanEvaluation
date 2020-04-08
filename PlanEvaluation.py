'''Run tests of the GUI interface
'''

#%% imports etc.
from pathlib import Path
from copy import deepcopy

from typing import Union, Dict, List
from typing import Union, Dict, List

import PySimpleGUI as sg

from build_plan_report import load_config, load_reports

from build_plan_report import load_config, load_reports
from build_plan_report import IconPaths, save_config
from build_plan_report import run_report, load_dvh
from build_plan_report import set_report_parameters
from plan_report import MatchHistory
from plan_report import MatchHistory
from plan_report import load_report_definitions, rerun_matching
from plan_data import NotDVH
from plan_data import get_default_units
from plan_data import NotDVH
from plan_data import get_default_units
from plan_data import get_laterality_exceptions, find_plan_files, dvh_info
from match_window import manual_match
from update_reports import update_report_definitions
from main_window import create_main_window, update_plan_header
from main_window import make_report_selection_list
from main_window import action_settings_config, update_report_header
from update_directories import change_default_locations, select_plan_file
from update_directories import select_report_file, select_save_file


Values = Dict[str, List[str]]
ConversionParameters = Dict[str, Union[str, float, None]]



#%% LOad Data and Run Main Window
def run_main_window(base_path, icons, config, config_file,
                    plan_dict, plan_parameters,
                    report_definitions, report_parameters):
        report = None
        active_plan = None
        selected_plan_desc = None
        history = MatchHistory()
        window = create_main_window(plan_dict, report_definitions)
        action_settings = action_settings_config()
        action_settings.set_status(window, 'Nothing Selected')

        while True:
            event, values = window.Read(timeout=2000)
            if event is None:
                break
            elif event in 'EXIT':
                window.close()
                break
            elif event == sg.TIMEOUT_KEY:
                continue
            elif event in 'Plan_tree':
                plan_desc = values['Plan_tree'][0]
                selected_plan_desc = plan_dict.get(plan_desc)
                if selected_plan_desc:
                    update_plan_header(window, selected_plan_desc)
                    action_settings.set_status(window, 'Plan Selected')
            elif event in 'report_selector':
                selected_report = values['report_selector']
                report = deepcopy(report_definitions.get(selected_report))
                if report:
                    update_report_header(window, report)
                    if active_plan:
                        action_settings.set_status(window, 'Plan and Report Ready')
                    else:
                        action_settings.set_status(window, 'Report Selected')
            elif event in 'load_plan':
                action_settings.set_status(window, 'Plan Loading')
                active_plan = load_dvh(selected_plan_desc, **plan_parameters)
                if active_plan:
                    if report:
                        action_settings.set_status(window, 'Plan and Report Ready')
                    else:
                        action_settings.set_status(window, 'Plan Loaded')
                else:
                    action_settings.set_status(window, 'Invalid Plan')
            elif event in 'match_structures':
                action_settings.set_status(window, 'Matching')
                rerun_matching(report, active_plan, history)
                report = manual_match(report, active_plan, icons)
                action_settings.set_status(window, 'Matched')
            elif event in 'generate_report':
                action_settings.set_status(window, 'Generating')
                default_directories = config.find(r'./DefaultDirectories')
                save_file = Path(default_directories.findtext('Save'))
                #save_file = select_save_file(default_directories)
                run_report(active_plan, report, save_file)
                action_settings.set_status(window, 'Generated')
            elif event in 'update_report_definitions':
                report_definitions = update_report_definitions(config, base_path)
                report_list = make_report_selection_list(report_definitions)
                window['report_selector'].update(values=report_list)
                window.refresh()
            elif event in 'Set Default Locations':
                default_directories = config.find(r'./DefaultDirectories')
                new_defaults = change_default_locations(default_directories)
                if new_defaults is not None:
                    default_directories = new_defaults
                    save_config(config, base_path, config_file)
            elif event in 'Select Plan DVH File':
                plan_file = select_plan_file(config)
                try:
                    plan_info = dvh_info(plan_file)
                except NotDVH:
                    sg.PopupError(f'{plan_file.name} is not a valid DVH file')
                else:
                    update_plan_header(window, plan_info)
            # FIXME Account for cancel button
            elif event in 'Load Report Definition File':
                default_directories = config.find(r'./DefaultDirectories')
                report_file = select_report_file(default_directories)
                report_dict = load_report_definitions(report_file,
                                                      report_parameters)
                report_definitions.update(report_dict)
                report_list = make_report_selection_list(report_definitions)
                window['report_selector'].update(values=report_list)
                window.refresh()
            elif event in 'Update all Report Definitions':
                report_definitions = update_report_definitions(config, base_path)
                report_list = make_report_selection_list(report_definitions)
                window['report_selector'].update(values=report_list)
                window.refresh()
            elif event in 'Set Save File Name':
                default_directories = config.find(r'./DefaultDirectories')
                save_file = select_save_file(default_directories)
                if save_file is not None:
                    if report:
                        report.save_file = Path(save_file)
                        update_report_header(window, report)

def main():
    '''Define Folder Paths, load report and plan data.
    '''
    base_path = Path.cwd()
    icon_path = base_path / 'icons'
    icons = IconPaths(icon_path)
    # %% Load Config file and Report definitions
    config_file = 'PlanEvaluationConfig.xml'
    config = load_config(base_path, config_file)

    code_exceptions = config.find('LateralityCodeExceptions')
    plan_parameters = dict(
        default_units=get_default_units(config),
        laterality_exceptions=get_laterality_exceptions(code_exceptions),
        name='Plan'
        )
    report_parameters = set_report_parameters(config)
    report_definitions = load_reports(config)
    plan_dict = find_plan_files(config)


    # %% Create and Run Main Window
    run_main_window(base_path, icons, config, config_file,
                    plan_dict, plan_parameters,
                    report_definitions, report_parameters)




if __name__ == '__main__':
    main()





