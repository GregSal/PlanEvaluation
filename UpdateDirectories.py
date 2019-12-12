#!/usr/bin/env python
''' Change the directories for DVH files, Report files , Save location
'''


from pathlib import Path
import xml.etree.ElementTree as ET
import PySimpleGUI as sg
from build_plan_report import load_config, save_config, update_reports
from plan_data import NotDVH


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
                          style=None) -> Path:
    '''Generate the window used to select directories.
    Keyword Arguments:
        header {str} -- Test at the top of the window. (default: {'Select a File:'})
        title {str} -- Window title (default: {'Select a File'})
        current_path {Path} -- Starting path and file (default: {Path.cwd()})
        file_options {tuple} -- File types available for selection (default: {(('All Files', '*.*'),)})
    Returns:
        Path -- The selected file, or None if a file is not selected.
    '''
    form_rows = [[sg.Text(header, **ELEMENT_STYLES['title'])],
                 [sg.InputText(key='SelectedFile', **ELEMENT_STYLES['input_text']),
                  sg.Button(
                      target='SelectedFile',
                      initial_folder=str(current_path),
                      file_types=file_options,
                      **ELEMENT_STYLES['FileBrowse']
                 )],
                 [sg.Column([], pad=(50,0), key='space'), sg.Ok(), sg.Cancel()]
                 ]
    window = sg.Window(title, form_rows, element_justification='center', finalize=True)
    window['space'].expand(expand_x=True, expand_y=False)
    event, values = window.read()
    window.close()
    if event in 'Ok':
        new_dir = Path(values['SelectedFile'])
        return new_dir
    return None


def select_plan_file(config: ET.Element) -> Path:
    '''
    Select a Plan DVH file to open.
    Arguments:
        config {ET.Element} -- COnfiguration data.
    Returns:
        Path -- The path to the selected file, or None if a file is not
        selected.
    '''
    default_directories = config.find(r'./DefaultDirectories')
    plan_name = default_directories.findtext('DVH_File')
    plan_dir = default_directories.findtext('DVH')
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


def select_report_file(config: ET.Element) -> Path:
    '''
    Select a Plan DVH file to open.
    Arguments:
        config {ET.Element} -- COnfiguration data.
    Returns:
        Path -- The path to the selected file, or None if a file is not
        selected.
    '''
    # FIXME select_report_file Not yet implemented
    default_directories = config.find(r'./DefaultDirectories')
    plan_name = default_directories.findtext('DVH_File')
    plan_dir = default_directories.findtext('DVH')
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

    # %% Create Test Window
    # These imports are here to avoid circular imports and are only used for
    # testing.
    from PlanEvaluation import create_plan_header, update_plan_header
    from plan_data import dvh_info
    test_layout = [
        [main_menu()],
        [create_plan_header()],
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
            # updated_config = change_default_locations(config) # FIXME change_default_locations not yet implemented
            # save_config(updated_config, base_path, 'TestConfig.xml')
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
            # Done To Here
            print('select_report_file(config)')
            # report_file = select_report_file(config)

#%% Scrap code
#locations = [
#    ('DVH', 'Directory', 'dvh_dir', 'DVH File Location'),
#    ('DVH_File', 'File', 'dvh_file', 'Default Plan DVH file.', (
#        ('All Files', '*.*'),
#        ('DVH Files', '*.dvh'),
#        ("Text Files", "*.txt")
#    )),
#    ('ReportPickleFile', 'File', 'report_file', 'Report Definition file.',
#     (('All Files', '*.*'), ('Pickle Files', '*.pkl'))),
#    ('Save', 'Directory', 'save_dir', 'Location to save Completed Reports')
#]
#locations = {
#    'DVH File Location': dict(
#        header='Select a Folder Containing Plan DVH files',
#        title='Plan DVH Directory'),
#    'Save Location': dict(
#        header='Select the directory to save the Plan Evaluation Report',
#        title='Save Location'),
#    'Report Location': dict(
#        header='Select the directory containing the Report definitions',
#        title='Report Location')
#}

##%% Defaults
#locations = [
#    ('DVH', 'Directory', 'dvh_dir', 'DVH File Location'),
#    ('DVH_File', 'File', 'dvh_file', 'Default Plan DVH file.', (
#        ('All Files', '*.*'),
#        ('DVH Files', '*.dvh'),
#        ("Text Files", "*.txt")
#    )),
#    ('ReportPickleFile', 'File', 'report_file', 'Report Definition file.',
#     (('All Files', '*.*'), ('Pickle Files', '*.pkl'))),
#    ('Save', 'Directory', 'save_dir', 'Location to save Completed Reports')
#]


#def file_selection(key_name: str, title='Select a File',
#                   current_path: Path = Path.cwd(), style=None,
#                   file_options=(('All Files', '*.*'),)) -> sg.Frame:
#    '''
#    '''
#    selection_row = [
#        sg.InputText(key=key_name),
#        sg.FileBrowse(target=key_name, initial_folder=str(current_dir),
#                      file_types=file_options)
#    ]
#    selection_group = sg.frame(title=title, layout=selection_row)
#    return selection_group


#def dir_selection_window(key_name: str, title: str,
#                         current_dir: Path = Path.cwd()) -> Path:
#    '''
#    '''
#    selection_row = [
#        sg.InputText(key=key_name),
#        sg.FolderBrowse(target=key_name, initial_folder=str(current_dir))
#    ]
#    return selection_row


# def dir_selection_window(key_name: str, title: str,
#                          current_dir: Path = Path.cwd()) -> Path:
#     '''
#     '''
#     selection_row = [
#         sg.InputText(key=key_name),
#         sg.FolderBrowse(target=key_name, initial_folder=str(current_dir))
#     ]
#     return selection_row

#     elif event in 'update_report_definitions':
#             report_definitions = update_report_definitions(config, base_path)
#             report_list = make_report_selection_list(report_definitions)
#             window['report_selector'].update(values=report_list)
#             window.refresh()

# %% Defaults
    # report = None
    # active_plan = None
    # selected_plan_desc = None

    # default_directories = config.find(r'./DefaultDirectories')
    # pickle_file = Path(default_directories.findtext('ReportPickleFile'))
    # plan_dvh_location = Path(default_directories.findtext('ReportPickleFile'))
    # save_location = Path(default_directories.findtext('Save'))
    # report_locations = get_report_dir_list(base_str, default_directories)
    # report_definitions = load_reports(config)
    # plan_dict = find_plan_files(config)
    # locations = [
    #     ('DVH', 'Directory', 'dvh_dir', 'DVH File Location'),
    #     ('DVH_File', 'File', 'dvh_file', 'Default Plan DVH file.', (
    #         ('All Files', '*.*'),
    #         ('DVH Files', '*.dvh'),
    #         ("Text Files", "*.txt")
    #     )),
    #     ('ReportPickleFile', 'File', 'report_file', 'Report Definition file.',
    #      (('All Files', '*.*'), ('Pickle Files', '*.pkl'))),
    #     ('Save', 'Directory', 'save_dir', 'Location to save Completed Reports')
    # ]

    # code_exceptions_def = config.find('LateralityCodeExceptions')
    # plan_parameters = dict(
    #     default_units=get_default_units(config),
    #     laterality_exceptions=get_laterality_exceptions(code_exceptions_def),
    #     name='Plan'
    # )

    #('ReportDefinitions', 'Directory', 'Report_dir', 'Report XML Locations')
    # header = 'Select the directory containing the Report definitions',
    # header = 'Select a Folder Containing Plan DVH files'


#def get_report_dir_list(default_directories: ET.Element,
#                        base_str: str = '') -> List[str]:
#    '''Generate a string list of directories containing report definitions.
#    The list is obtained from the Config .xml file.
#    The directories in the string list replace the top directory path,
#    given by base_str, with: ".\".
#    Arguments:
#        default_directories {ET.Element} -- Sub-Element of the Config .xml file
#            containing the default directory paths.
#        base_str {str} -- A string path to the top directory referenced.
#    '''
#    report_locations = list()
#    report_path_element = default_directories.find('ReportDefinitions')
#    for location in report_path_element.findall('Directory'):
#        report_dir = Path(location.text).resolve()
#        report_dir_str = str(report_dir).replace(base_str, '.')
#        report_locations.append(report_dir_str)
#    return report_locations


#def select_locations(report_locations, base_str):
#    window = selection_window(report_locations, base_str)
#    done = False
#    dir_list = window['ReportDirs']
#    while not done:
#        event, values = window.read(timeout=200)
#        if event == sg.TIMEOUT_KEY:
#            continue
#        elif event in 'Cancel':
#            done = True
#            report_locations = None
#        elif event in 'Submit':
#            done = True
#            report_locations = [Path(dir) for dir in dir_list.GetListValues()]
#        elif event in 'Delete':
#            remove_items = values['ReportDirs']
#            updated_list = [dir for dir in dir_list.GetListValues()
#                            if dir not in remove_items]
#            dir_list.Update(values=updated_list)
#            window.refresh()
#        elif event in 'Add':
#            add_item = values['NewReportDir']
#            report_dir = Path(add_item).resolve()
#            report_dir_str = str(report_dir).replace(base_str, '.\\')
#            updated_list = set(dir_list.GetListValues())
#            updated_list.add(report_dir_str)
#            dir_list.Update(values=list(updated_list))
#            window.refresh()
#    window.close()
#    return report_locations


# %% Run Tests

if __name__ == '__main__':
    main()
