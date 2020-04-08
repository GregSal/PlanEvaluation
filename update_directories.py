#!/usr/bin/env python
''' Change the directories for DVH files, Report files , Save location
'''

#%% imports etc.
from pathlib import Path
from copy import deepcopy
from typing import Tuple, List, NamedTuple
import xml.etree.ElementTree as ET
import PySimpleGUI as sg
from build_plan_report import load_config, save_config, load_reports
from build_plan_report import set_report_parameters
from plan_data import NotDVH
from plan_report import load_report_definitions
from update_reports import update_report_definitions


#%% GUI Formatting
sg.change_look_and_feel('LightGreen')
sg.SetOptions(element_padding=(0, 0), margins=(0, 0))

ELEMENT_STYLES = {
    'frame': dict(
        title_color='blue',
        background_color='LightBlue1',
        title_location=sg.TITLE_LOCATION_TOP_LEFT,
        relief=sg.RELIEF_GROOVE,
        border_width=6,
        font=('Arial Black', 14, 'bold'),
        element_justification='left'
        ),
    'title': dict(
        auto_size_text=True,
        #relief=sg.RELIEF_RAISED,
        font=('Arial Black', 12, 'bold'),
        text_color='blue',
        #background_color='LightBlue1',
        border_width=6,
        justification='center',
        #pad=(10, 10)
        ),
    'input_text': dict(
        default_text="",
        size=(60, 1),
        disabled=False,
        password_char="",
        justification='right',
        background_color='Slategray1',
        text_color='black',
        font=('Tahoma', 11, 'normal'),
        tooltip=None,
        change_submits=False,
        enable_events=False,
        do_not_clear=True,
        focus=False,
        pad=((20, 5), (5, 5)),
        right_click_menu=None,
        visible=True,
        metadata=None
        ),
    'text': dict(
        size=(60, 1),
        auto_size_text=False,
        relief=sg.RELIEF_SUNKEN,
        font=('Tahoma', 11, 'normal'),
        text_color='black',
        background_color='Slategray1',
        border_width=3,
        justification='left',
        pad=((20, 5), (10, 10))
        ),
    'button': dict(
        size=(15, 1),
        auto_size_button=False,
        font=('Georgia', 11, 'bold'),
        text_color='black',
        background_color='steel blue',
        border_width=3,
        pad=((0, 20), (5, 5))
        ),
    'FileBrowse': dict(
        button_text='Browse',
        button_type=sg.BUTTON_TYPE_BROWSE_FILE,
        #target=(ThisRow, -1),
        #initial_folder=initial_folder,
        #file_types=(("ALL Files", "*.*"),),
        tooltip=None,
        disabled=False,
        change_submits=False,
        enable_events=False,
        image_filename=None,
        image_data=None,
        image_size=(None, None),
        image_subsample=None,
        border_width=1,
        size=(10, 1),
        auto_size_button=False,
        button_color=('black', 'steel blue'),
        #use_ttk_buttons=None,
        font=('Georgia', 11, 'normal'),
        bind_return_key=False,
        focus=False,
        pad=((0, 20), (10, 10)),
        visible=True,
        metadata=None
        ),
    'popup': dict(
        button_color=None,
        background_color=None,
        text_color=None,
        button_type=0,
        auto_close=False,
        auto_close_duration=None,
        custom_text=(None, None),
        non_blocking=False,
        icon=None,
        line_width=None,
        font=None,
        no_titlebar=False,
        grab_anywhere=False,
        keep_on_top=False,
        location=(None, None)
        )
    }


#%% Functional windows
def file_selection_window(header='Select a File:',
                          title='Select a File',
                          current_path: Path = Path.cwd(),
                          file_options=(('All Files', '*.*'),),
                          path_type: str = 'Load File')->Path:
    '''Generate the window used to select directories.
    Keyword Arguments:
        header {str} -- Test at the top of the window. 
            default: {'Select a File:'}
        title {str} -- Window title (default: {'Select a File'})
        current_path {Path} -- Starting path and file (default: {Path.cwd()})
        file_options {tuple} -- File types available for selection 
            default: {(('All Files', '*.*'),)}
    Returns:
        Path -- The selected file, or None if a file is not selected.
    '''
    button_style = ELEMENT_STYLES['FileBrowse'].copy()
    button_style['initial_folder'] = str(current_path)
    if path_type in 'Save File':
        button_style['button_type'] = sg.BUTTON_TYPE_SAVEAS_FILE
        button_style['file_types'] = file_options
    else:
        button_style['button_type'] = sg.BUTTON_TYPE_BROWSE_FILE
        button_style['file_types'] = file_options

    form_rows = [[sg.Text(header, **ELEMENT_STYLES['title'])],
                 [sg.InputText(key='SelectedFile',
                               **ELEMENT_STYLES['input_text']),
                  sg.Button(target='SelectedFile', **button_style)
                 ],
                 [sg.Column([], pad=(50,0), key='space'),
                  sg.Ok(), sg.Cancel()]
                ]
    window = sg.Window(title, form_rows, element_justification='center',
                       finalize=True)
    window['space'].expand(expand_x=True, expand_y=False)
    event, values = window.read()
    window.close()
    if event in 'Ok':
        new_dir = Path(values['SelectedFile'])
        return new_dir
    return None


def select_plan_file(config: ET.Element)->Path:
    '''
    Select a Plan DVH file to open.
    Arguments:
        config {ET.Element} -- COnfiguration data.
    Returns:
        Path -- The path to the selected file, or None if a file is not
        selected.
    '''
    plan_name = config.findtext(r'.//DVH_File')
    plan_dir = config.findtext(r'.//DVH')
    # Set the initial directory and file
    if plan_dir is None:
        starting_dir = Path.cwd()
    elif plan_name is None:
        starting_dir = Path(plan_dir)
    else:
        starting_dir = Path(plan_dir) / plan_name
    dvh_plan = file_selection_window(
        header='Select a DVH Plan file to load',
        title='Select DVH Plan File',
        current_path=starting_dir,
        file_options=(
            ('DVH Files', '*.dvh'),
            ('All Files', '*.*'),
            ("Text Files", "*.txt")
            )
        )
    return dvh_plan


def select_report_file(default_directories: ET.Element)->Path:
    '''
    Select a Report definition file to open.
    Arguments:
        config {ET.Element} -- COnfiguration data.
    Returns:
        Path -- The path to the selected file, or None if a file is not
        selected.
    '''
    report_dir = default_directories.findtext('ReportDefinitions')
    # Set the initial directory and file
    if report_dir is None:
        starting_dir = Path.cwd()
    else:
        starting_dir = Path(report_dir)
    report_file = file_selection_window(
        header='Select a Report Definition file to load',
        title='Select Report Definition File',
        current_path=starting_dir,
        file_options=(('XML Files', '*.xml'),)
        )
    return report_file


def select_save_file(default_directories: ET.Element)->Path:
    '''
    Select the name of the file to save the completed report in.
    Arguments:
        default_directories {ET.Element} -- Configuration data.
    Returns:
        Path -- The path to the selected file, or None if a file is not
        selected.
    '''
    save_file = default_directories.findtext('Save')
    # Set the initial directory and file
    if save_file is None:
        starting_dir = Path.cwd()
    else:
        starting_dir = Path(save_file)
    new_save_file = file_selection_window(
        header='Save the Completed Report',
        title='Save Report As',
        current_path=starting_dir,
        file_options=(('Excel Files', '*.xlsx'),),
        path_type='Save File'
        )
    return new_save_file


def get_save_file(default_directories: ET.Element)->Path:
    '''
    Get the default name of the file to save the completed report in.
    Arguments:
        default_directories {ET.Element} -- Configuration data.
    Returns:
        Path -- The path to the selected file, or None if a file is not
        selected.
    '''
    save_file = default_directories.findtext('Save')
    # Set the initial directory and file
    if save_file is None:
        starting_dir = Path.cwd()
    else:
        starting_dir = Path(save_file)
    new_save_file = file_selection_window(
        header='Save the Completed Report',
        title='Save Report As',
        current_path=starting_dir,
        file_options=(('Excel Files', '*.xlsx'),),
        path_type='Save File'
        )
    return new_save_file

class DfltPath(NamedTuple):
    '''Individual File/Directory selection Frame parameters.
    Arguments:
        NamedTuple {[type]} -- [description]
    '''
    xml_element: str # reference to <config><DefaultDirectories> sub-element
    path_type: str # One of 'Directory', 'Read File' or 'Save File'
    widget_name: str # Reference for the Window
    frame_title: str # Text for labeled frame
    file_types: List[Tuple[str, str]] = None


def path_selection_frame(default_directories: ET.Element,
                         path_param: DfltPath)->sg.Frame:
    button_style = ELEMENT_STYLES['FileBrowse'].copy()
    button_style['target'] = path_param.widget_name
    # Set the starting path
    default_path = default_directories.findtext(path_param.xml_element)
    if default_path is None:
        button_style['initial_folder'] = Path.cwd()
    else:
        button_style['initial_folder'] = Path(default_path)
    # Set the path type
    if path_param.path_type in 'Directory':
        button_style['button_type'] = sg.BUTTON_TYPE_BROWSE_FOLDER
    elif path_param.path_type in 'Save File':
        button_style['button_type'] = sg.BUTTON_TYPE_SAVEAS_FILE
        button_style['file_types'] = path_param.file_types
    else:
        button_style['button_type'] = sg.BUTTON_TYPE_BROWSE_FILE
        button_style['file_types'] = path_param.file_types
    button = sg.Button(**button_style)
    input = sg.InputText(key=path_param.widget_name,
                         **ELEMENT_STYLES['input_text'])
    selection_frame = sg.Frame(title=path_param.frame_title,
                               layout=[[input, button]],
                               **ELEMENT_STYLES['frame'])
    return selection_frame


def path_selection_window(default_directories: ET.Element,
                          locations: List[DfltPath])->sg.Window:
    layout = []
    for path_param in locations:
        selection_frame = path_selection_frame(default_directories, path_param)
        layout.append([selection_frame])
    layout.append([sg.Column([], pad=(50,3), key='space'),
                   sg.Ok(pad=(3,3)), sg.Cancel(pad=(3,3))])
    window = sg.Window('Set Default Files and Directories', layout,
                       element_justification='center',
                       element_padding=(5, 0), finalize=True)
    window['space'].expand(expand_x=True, expand_y=False)
    return window


def change_default_locations(default_directories: ET.Element)->ET.Element:
    locations = [
        DfltPath('DVH', 'Directory', 'dvh_dir', 'DVH File Location'),
        DfltPath('DVH_File', 'Load File', 'dvh_file',
                 'Default Plan DVH file.', (
                     ('DVH Files', '*.dvh'),
                     ('All Files', '*.*'),
                     ("Text Files", "*.txt")
                     )),
        DfltPath('ReportPickleFile', 'Load File', 'report_file',
                 'Report Definition file.', (
                     ('Pickle Files', '*.pkl'),
                     ('All Files', '*.*')
                     )),
        DfltPath('Save', 'Directory', 'Save File',
                 'Location to save Completed Reports', (
                     ('Excel Files', '*.xlsx'),
                     ('All Files', '*.*')
                     ))
        ]
    window = path_selection_window(default_directories, locations)
    done=False
    while not done:
        event, values = window.read(timeout=200)
        if event == sg.TIMEOUT_KEY:
            window.refresh()
        elif event in 'Cancel':
            done = True
            default_directories = None
        elif event in 'Ok':
            done = True
            for path_param in locations:
                #FIXME change "path_param.xml_element" to an XPath search from the top:
                # // Selects all subelements, on all levels beneath the current element. 
                # For example, .//egg selects all egg elements in the entire tree.
                path_element = default_directories.find(path_param.xml_element) 
                new_default = values[path_param.widget_name]
                path_element.text = new_default
    window.close()
    return default_directories


#%% Main Menu
def main_menu():
    menu_def = [['&File', ['Set &Default Locations', '---', 'Select &Plan DVH File',
                           'Load &Report Definition File',
                           '&Update all Report Definitions',
                           'Set &Save File Name', 'E&xit']]]
    return sg.Menu(menu_def, tearoff=False, pad=(20, 1), key='menu')


#%% Test the Directories windows
def main():
    '''Define Folder Paths, load report and plan data.
    '''
    # %% Initial directories
    base_path = Path.cwd()

    # %% Load Config file
    config_file = 'PlanEvaluationConfig.xml'
    config = load_config(base_path, config_file)
    test_config_file = 'TestConfig.xml'
    default_directories = config.find(r'./DefaultDirectories')


    # %% Load Report Definitions
    report_definitions = load_reports(config)
    report_parameters = set_report_parameters(config)
    report_name = 'SABR 54 in 3'
    report = deepcopy(report_definitions[report_name])

    # %% Default Path Info

    # DefaultDirectories Element in Config
    #  <DefaultDirectories>
    #    <DVH>.\DVH Files</DVH>
    #    <DVH_File>plan.dvh</DVH_File>
    #    <ReportDefinitions>
    #      <Directory>.\Data</Directory>
    #    </ReportDefinitions>
    #    <ReportTemplates>.\Data</ReportTemplates>
    #    <ReportPickleFile>.\Data\Reports.pkl</ReportPickleFile>
    #    <Save>.\Output</Save>
    #  </DefaultDirectories>


    #header='Select a Folder Containing Plan DVH files'
    #header='Select the directory to save the Plan Evaluation Report'
    #header='Select the directory containing the Report definitions'


    # %% Create Test Window
    # These imports are here to avoid circular imports and are only used for
    # testing.
    from main_window import create_plan_header, update_plan_header
    from main_window import make_report_selection_list, create_report_header
    from main_window import make_actions_column, update_report_header
    from plan_data import dvh_info
    test_layout = [
        [main_menu()],
        [create_plan_header(),
        create_report_header(),
        make_actions_column(report_definitions)],
        [sg.Exit()]
        ]
    window = sg.Window('Plan Evaluation',
                       layout=test_layout,
                       resizable=True,
                       debugger_enabled=True,
                       finalize=True,
                       element_justification="left")

    # %% Run Test Window
    while True:
        event, values = window.Read(timeout=2000)
        if event is None:
            break
        elif event == sg.TIMEOUT_KEY:
            continue
        elif event in 'Exit':
            window.close()
            break
        elif event in 'Set Default Locations':
            print('change_default_locations(config)')
            new_defaults = change_default_locations(default_directories)
            if new_defaults is not None:
                default_directories = new_defaults
                save_config(config, base_path, test_config_file)
        elif event in 'Select Plan DVH File':
            print('select_plan_file(config)')
            plan_file = select_plan_file(config)
            try:
                plan_info = dvh_info(plan_file)
            except NotDVH:
                sg.PopupError(f'{plan_file.name} is not a valid DVH file')
            else:
                update_plan_header(window, plan_info)
        elif event in 'Load Report Definition File':
            print('select_report_file(config)')
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
            print('Set Save File Name')
            save_file = select_save_file(default_directories)
            if save_file is not None:
                if report:
                    report.save_file = Path(save_file)    
                    update_report_header(window, report)


# %% Run Tests
if __name__ == '__main__':
    main()
