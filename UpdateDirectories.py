#!/usr/bin/env python
from pathlib import Path
import PySimpleGUI as sg
from build_plan_report import load_config, update_reports
''' Change the directories for DVH files, Report files , Save location
  <DefaultDirectories>
    <DVH>..\DVH Files</DVH>
    <DVH_File>plan.dvh</DVH_File>
    <ReportDefinitions>
      <Directory>.\Data</Directory>
    </ReportDefinitions>
    <ReportTemplates>.\Data</ReportTemplates>
    <ReportPickleFile>.\Data\Reports.pkl</ReportPickleFile>
    <Save>..\Output</Save>
  </DefaultDirectories>
  '''


def second_window():

    layout = [[sg.Text('The second form is small \nHere to show that opening a window using a window works')],
              [sg.OK()]]

    window = sg.Window('Second Form', layout)
    event, values = window.read()
    window.close()


def test_menus():

    sg.change_look_and_feel('LightGreen')
    sg.set_options(element_padding=(0, 0))

    # ------ Menu Definition ------ #
    menu_def = [['&File', ['&DVH File Location', '&Save Location', '&Report Location', 'E&xit']]

    # ------ GUI Defintion ------ #
    layout = [
        [sg.Menu(menu_def, tearoff=False, pad=(20, 1))],
        [sg.Output(size=(60, 20))],
    ]

    window = sg.Window("Windows-like program",
                       layout,
                       default_element_size=(12, 1),
                       auto_size_text=False,
                       auto_size_buttons=False,
                       default_button_element_size=(12, 1))

    # ------ Loop & Process button menu choices ------ #
    while True:
        event, values = window.read()
        if event in (None, 'Exit'):
            return
        print('Event = ', event)
        # ------ Process menu choices ------ #
        if event == 'About...':
            window.disappear()
            sg.popup('About this program', 'Version 1.0',
                     'PySimpleGUI rocks...', grab_anywhere=True)
            window.reappear()
        elif event == 'Open':
            filename = sg.popup_get_file('file to open', no_window=True)
            print(filename)
        elif event == 'Properties':
            second_window()

    window.close()


test_menus()

def get_report_dir_list(default_directories: ET.Element,
                        base_str: str = '')->List[str]:
    '''Generate a string list of directories containing report definitions.
    The list is obtained from the Config .xml file.
    The directories in the string list replace the top directory path,
    given by base_str, with: ".\".
    Arguments:
        default_directories {ET.Element} -- Sub-Element of the Config .xml file
            containing the default directory paths.
        base_str {str} -- A string path to the top directory referenced.
    '''
    report_locations = list()
    report_path_element = default_directories.find('ReportDefinitions')
    for location in report_path_element.findall('Directory'):
        report_dir = Path(location.text).resolve()
        report_dir_str = str(report_dir).replace(base_str, '.')
        report_locations.append(report_dir_str)
    return report_locations


def selection_window(report_locations: list[str], base_str: str = '')->sg.Window:
    '''Generate the window used to select directories containing report
    definitions.
    '''
    form_rows = [[sg.Text('Select Folders Containing Evaluation Reports')],
                 [sg.Listbox(key='ReportDirs',
                             select_mode=sg.LISTBOX_SELECT_MODE_MULTIPLE,
                             auto_size_text=False,
                             size=(40, 5),
                             values=report_locations),
                  sg.VerticalSeparator(),
                  sg.Column([
                      [sg.Button(button_text='Delete', size=(15, 1), pad=(10, 5))],
                      [sg.Button(button_text='Add', size=(15, 1), pad=(10, 5))],
                      ])
                 ],
                 [sg.InputText(key='NewReportDir'),
                  sg.FolderBrowse(target='NewReportDir',
                                  initial_folder=base_str)],
                 [sg.Submit(), sg.Cancel()]
                ]
    window = sg.Window('Update Report Definitions', form_rows)
    return window


def select_locations(report_locations, base_str):
    window = selection_window(report_locations, base_str)
    done=False
    dir_list = window['ReportDirs']
    while not done:
        event, values = window.read(timeout=200)
        if event == sg.TIMEOUT_KEY:
            continue
        elif event in 'Cancel':
            done=True
            report_locations = None
        elif event in 'Submit':
            done=True
            report_locations = [Path(dir) for dir in dir_list.GetListValues()]
        elif event in 'Delete':
            remove_items = values['ReportDirs']
            updated_list = [dir for dir in dir_list.GetListValues()
                            if dir not in remove_items]
            dir_list.Update(values=updated_list)
            window.refresh()
        elif event in 'Add':
            add_item = values['NewReportDir']
            report_dir = Path(add_item).resolve()
            report_dir_str = str(report_dir).replace(base_str, '.\\')
            updated_list = set(dir_list.GetListValues())
            updated_list.add(report_dir_str)
            dir_list.Update(values=list(updated_list))
            window.refresh()
    window.close()
    return report_locations


#%% Main
def main():
    '''Define Folder Paths, load report and plan data.
    '''
    base_path = Path.cwd().resolve()
    base_str = str(base_path)
    #%% Load Config file and Report definitions
    config_file = 'PlanEvaluationConfig.xml'
    config = load_config(base_path, config_file)
    default_directories = config.find(r'./DefaultDirectories')
    pickle_file = Path(default_directories.findtext('ReportPickleFile'))
    report_locations = get_report_dir_list(base_str, default_directories)
    report_locations = select_locations(report_locations, base_str)
    if report_locations:
        report_paths = [Path(dir).resolve() for dir in report_locations]
        report_definitions = update_reports(config, report_paths, pickle_file)
    else:
        report_definitions = None





if __name__ == '__main__':
    main()

