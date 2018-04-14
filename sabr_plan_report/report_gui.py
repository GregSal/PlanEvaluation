'''
Created on Aug 26 2017

@author: Greg Salomons
GUI interface for DirScan.

Classes
    DirGui:
        Primary GUI window
        sub class of TKinter.Frame

'''

import tkinter.filedialog as tkf
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from functools import partial

from plan_eval_parameters import PlanEvalParameters
from plan_eval_parameters import FileTypeError
from file_type_definitions import FileTypes


class SelectFileDialgue(object):
    '''Creates and runs a custom file or directory selection GUI.
    '''
    def __init__(self, master_frame=None, heading='',
                 starting_directory=None, update_method=print):
        '''configure the base dialogue parameters.
        '''
        self.parameters = {
            'parent': master_frame,
            'title': heading}
        if starting_directory:
            self.parameters['initialdir'] = Path(starting_directory)
        else:
            self.parameters['initialdir'] = Path.cwd()
        self.dialogue_type = None
        self.store_selection = update_method

    def choose_dialogue_type(self, action, filetypes):
        '''Set the appropriate dialogue box to use.
        '''
        if 'dir' in filetypes:
            self.dialogue_type = tkf.askdirectory
            self.parameters['mustexist'] = True
        elif 'save' in action:
            self.dialogue_type = tkf.asksaveasfilename
            self.parameters['confirmoverwrite'] = True
        else:
            self.dialogue_type = tkf.askopenfilename

    def choose_file_type(self, filetypes):
        '''Set the valid file types for the dialogue box.
        '''
        if 'dir' in filetypes:
            # filetypes is not defined for directory dialogue
            self.parameters.pop('filetypes', None)
        elif isinstance(filetypes, str):
            self.parameters['filetypes'] = FileTypes([filetypes])
        else:
            self.parameters['filetypes'] = FileTypes(list(filetypes))

    def set_initial_values(self, initial_file=None, extension=None):
        '''Set default file and extension values
        '''
        if initial_file:
            initial_file = Path(initial_file)
            self.parameters['initialdir'] = initial_file.parent
            self.parameters['initialfile'] = initial_file.name
            self.parameters['defaultextension'] = initial_file.suffix
        if extension:
            self.parameters['defaultextension'] = extension

    def call_dialogue(self):
        '''Call the dialogue with the set parameters and return the resulting
        file or directory.
        '''
        selected_file_string = self.dialogue_type(**self.parameters)
        if selected_file_string:
            try:
                file_select = Path(selected_file_string)
                self.store_selection(file_select)
            except (TypeError, FileTypeError) as err:
                print("OS error: {0}".format(err))
            else:
                master_frame = self.parameters['parent']
                master_frame.set(selected_file_string)


class ReportGuiSubFrame(tk.LabelFrame): # pylint: disable=too-many-ancestors
    '''GUI classes used for defining sub class of frames to be placed inside
    the main GUI.
    '''
    var_type_dict = {
        'string': tk.StringVar,
        'int': tk.IntVar
        }

    def __init__(self, owner_frame, form_title=None, var_type='string'):
        '''Build the frame and define the access variable
        '''
        super().__init__(owner_frame, text=form_title)
        var_select = self.var_type_dict[var_type]
        self.select_var = var_select()

    def set(self, select_value: str):
        '''Set the path_string frame variable.
        '''
        self.select_var.set(select_value)

    def get(self):
        '''Get the path_string frame variable.
        '''
        return self.select_var.get()

    def build(self, select_cmd=None):
        '''Configure the GUI frame and add sub-frames.
        This method is to be overwritten for each sub-class.
        '''
        new_entry = tk.Entry(self, textvariable=self.select_var,
                             width=100)
        action = tk.Button(self, text='Run', command=select_cmd)
        new_entry.pack(fill=tk.X, padx=10, pady=5, side=tk.LEFT)
        action.pack(padx=5, pady=5, side=tk.RIGHT)


class ReportGuiFrame(tk.Frame): # pylint: disable=too-many-ancestors
    '''Master class for primary sub-frames and for main GUI.
    '''

    def __init__(self, report_param: PlanEvalParameters, master=None):
        '''Create the DIR Scan GUI and set the initial parameters
        '''
        super().__init__(master)
        self.master = master
        self.data = report_param
        self.empty_label = None

    def build(self, run_cmd=None):
        '''Configure the GUI frame and add sub-frames.
        This method is to be overwritten for each sub-class.
        '''
        empty_label = ReportGuiSubFrame(self, 'Your text goes here')
        empty_label.set(self.data.source)
        empty_label.build(run_cmd)
        empty_label.pack()

        self.empty_label = empty_label

    def update(self):
        '''Update all data values from the GUI sub-frames.
        This method is to be overwritten for each sub-class.
        '''
        self.data.update_source(self.empty_label.get())


class FileSelectGui(ReportGuiSubFrame): # pylint: disable=too-many-ancestors
    '''GUI frame for selecting a file or directory.
    sub class of TKinter.LabelFrame.
    used inside the InputPathsFrame and OutputPathsFrame.
    '''
    def build(self, select_cmd):
        file_show = tk.Entry(self, textvariable=self.select_var, width=100)
        select_file = tk.Button(self, text='Browse', command=select_cmd)
        file_show.pack(fill=tk.X, padx=10, pady=5, side=tk.LEFT)
        select_file.pack(padx=5, pady=5, side=tk.RIGHT)


class InputPathsFrame(ReportGuiFrame): # pylint: disable=too-many-ancestors
    '''GUI frame for selecting the DVH file to read.
    used inside the main GUI.
    '''
    def build(self):
        '''Build the frame to select the plan DVH file to read.
        '''
        select_file_header = 'Select the DVH file to read.'
        select_file = FileSelectGui(self, select_file_header)

        # Define the file source dialogue
        if self.data.dvh_file:
            select_file.set(str(self.data.dvh_file))
            initial_dir = None
        else:
            initial_dir = str(self.data.base_path)
        filetypes = 'DVH File'
        action = 'open'
        dialogue_settings = {'master_frame': select_file,
                             'heading': select_file_header,
                             'starting_directory': initial_dir,
                             'update_method': self.data.update_dvh_file}
        file_select_dialog = \
            SelectFileDialgue(**dialogue_settings)
        file_select_dialog.choose_dialogue_type(action, filetypes)
        file_select_dialog.choose_file_type(filetypes)
        file_select_dialog.set_initial_values(initial_file=select_file.get())

        # Add the file source dialogue
        select_file.build(file_select_dialog.call_dialogue)
        select_file.pack()
        self.select_file = select_file

    def update(self):
        '''Update all data values from the GUI sub-frames.
        '''
        self.data.update_dvh_file(self.select_file.get())


class OutputFileSelectGui(ReportGuiSubFrame): # pylint: disable=too-many-ancestors
    '''GUI frame for selecting the file to save the report in.
    used inside the main GUI.
    '''
    def __init__(self, owner_frame, header=None, var_type='string'):
        '''Build the frame and define the select and file path variable.
        '''
        super().__init__(owner_frame, form_title=header)

    def build(self, select_cmd):
        '''Build the frame to select the save file name
        '''
        # Add the file selection
        file_show = tk.Entry(self, textvariable=self.select_var, width=100)
        select_file = tk.Button(self, text='Browse', command=select_cmd)
        file_show.pack(fill=tk.X, padx=10, pady=5, side=tk.LEFT)
        select_file.pack(padx=5, pady=5, side=tk.RIGHT)

class OutputPathsFrame(ReportGuiFrame): # pylint: disable=too-many-ancestors
    '''GUI frame for selecting the files to store the output from
    Scan and Parse.
    used inside the main GUI.
    '''
    def build(self):
        '''Build the frame to select a file or directory.
        Add the form to select a directory to scan.
        '''
        # Add frame to select a file to save file data from the parse output
        file_data_header = 'Set the file name to save the plan report.'
        file_data_select = OutputFileSelectGui(self, file_data_header)

        # Define the file source dialogue
        if self.data.save_file:
            file_data_select.set(str(self.data.save_file))
            initial_dir = None
        else:
            initial_dir = str(self.data.base_path)
        filetypes = 'Excel Files'
        action = 'save'
        dialogue_settings = {'master_frame': file_data_select,
                             'heading': file_data_header,
                             'starting_directory': initial_dir,
                             'update_method': self.data.update_save_file}
        file_select_dialog = SelectFileDialgue(**dialogue_settings)
        file_select_dialog.choose_dialogue_type(action, filetypes)
        file_select_dialog.choose_file_type(filetypes)
        file_select_dialog.set_initial_values(
            initial_file=file_data_select.get(),
            extension='.xls')

        # Add the file source dialogue
        file_data_select.build(file_select_dialog.call_dialogue)
        file_data_select.pack()
        self.file_data_output = file_data_select

    def update(self):
        '''Update all data values from the GUI sub-frames.
        This method is to be overwritten for each sub-class.
        '''
        self.data.update_save_file(self.file_data_output.get())

class SelectReportFrame(ReportGuiSubFrame): # pylint: disable=too-many-ancestors
    '''GUI frame for selecting the report to use
    '''
    def build(self, report_list):
        '''Build the frame to display the report names for selection.
        '''
        for index, report_name in enumerate(report_list):
            selection = tk.Radiobutton(self, text=report_name,
                                       variable=self.select_var, value=index)
            selection.grid(column=1, row=index+1, pady=0, padx=0, sticky=tk.E)

class ReportSelectionFrame(ReportGuiFrame): # pylint: disable=too-many-ancestors
    '''Build the frame used to select the report to use.
    '''
    # Add frame to select a file to save file data from the parse output
    def build(self):
        report_name_header = 'Select the appropriate Evaluation.'
        report_select = SelectReportFrame(self, report_name_header, var_type='int')
        report_select.set(str(self.data.report_name))
        report_select.build(self.data.report_list)
        report_select.pack()
        self.report_select = report_select

    def update(self):
        '''Update all data values from the GUI sub-frames.
        This method is to be overwritten for each sub-class.
        '''
        selected_report = self.data.report_list[self.report_select.get()]
        self.data.update_report_name(selected_report)


class ActionButtonsFrame(ReportGuiFrame): # pylint: disable=too-many-ancestors
    '''Add the buttons to generate the report and finish.
    '''
    def build(self):
        '''Configure the GUI frame and add sub-frames.
        This method is to be overwritten for each sub-class.
        '''
        action_label = 'Run Plan Evaluation'
        run = self.master.run_method
        done = self.master.done_method
        self.run_button = tk.Button(self, text=action_label, command=run)
        self.done_button = tk.Button(self, text='Done', command=done)
        self.run_button.grid(column=1, row=1, padx=5)
        self.done_button.grid(column=2, row=1, padx=5)

    def update(self):
        '''Update all data values from the GUI sub-frames.
        This method is to be overwritten for each sub-class.
        '''
        self.run_button.config(text='action_label')

class StatusTextFrame(ReportGuiFrame):  # pylint: disable=too-many-ancestors
    '''GUI frame for indicating current status of the Actions.
    '''
    def build(self, initial_status='Enter Selections'):
        '''Build the frame to display the status.
        '''
        self.master.status_text.set(initial_status)
        status_box = tk.Label(self, textvariable=self.master.status_text)
        status_box.pack()


class DirGui(tk.Frame): # pylint: disable=too-many-ancestors
    '''TKinter GUI class used for the plan evaluation program main GUI.
    '''
    def __init__(self, scan_param: PlanEvalParameters, master, run_cmd):
        '''Create the plan evaluation GUI and set the initial parameters
        '''
        super().__init__(master)
        self.data = scan_param
        self.run_method = partial(self.update_and_run, run_cmd)
        self.done_method = master.destroy
        self.status_text = tk.StringVar()
        self.report_select = None
        self.input_select = None
        self.output_select = None

    def window_format(self):
        '''Format and label main GUI window.
        Add a window title,
        Add a window icon,
        Add a header label
        '''
        root = self._root()
        root.title("SABR Plan Evaluation")
        # Add a window icon
        ico_pict = r'.\DVH.png'
        root.iconphoto(root, tk.PhotoImage(file=ico_pict))
        # Add Top header
        header = tk.Label(self, text='SABR Plan Evaluation')
        header.config(font=('system', 20, 'bold'))
        header.grid(column=1, row=1, columnspan=3)

    def build(self):
        '''Configure the main GUI window and add sub-frames.
        '''
        self.window_format()
        input_select_frame = InputPathsFrame(self.data, self)
        input_select_frame.build()
        input_select_frame.grid(column=1, row=2, columnspan=3,
                                padx=10, sticky=tk.W)
        self.input_select = input_select_frame

        report_select_frame = ReportSelectionFrame(self.data, self)
        report_select_frame.build()
        report_select_frame.grid(column=1, row=3, columnspan=2,
                                 padx=10, sticky=tk.W)
        self.report_select = report_select_frame

        output_select_frame = OutputPathsFrame(self.data, self)
        output_select_frame.build()
        output_select_frame.grid(column=1, row=4, columnspan=3,
                                 padx=10, sticky=tk.W)
        self.output_select = output_select_frame

        action_buttons_frame = ActionButtonsFrame(self.data, self)
        action_buttons_frame.build()
        action_buttons_frame.grid(column=1, row=5, columnspan=3, pady=2)

        status_message_frame = StatusTextFrame(self.data, self)
        status_message_frame.build()
        status_message_frame.grid(column=1, row=6, columnspan=3,
                                  padx=10, sticky=tk.W)

    def update(self):
        '''Update all scan and parse parameters from the GUI frames.
        '''
        self.input_select.update()
        self.report_select.update()
        self.output_select.update()

    def update_and_run(self, run_cmd):
        '''Set all values for the scan parameters from the GUI.
        '''
        self.update()
        # Perhaps split up scan and parse commands
        run_cmd(self.data)


def activate_gui(scan_param: PlanEvalParameters, run_cmd):
    '''Activate the GUI and return the selected parameters.
    '''
    root = tk.Tk()
    dir_gui = DirGui(scan_param, root, run_cmd)
    dir_gui.build()
    dir_gui.pack()
    root.mainloop()
    return dir_gui


def main():
    '''Test the activate_gui function call.
    '''
    def param_string(scan_param: PlanEvalParameters):
        '''Display the parameters in a pop-up message a test function.
        '''
        param_dict = {
            'base_path': str(scan_param.base_path),
            'report_definition_file': str(scan_param.report_definition_file),
            'report_list': str(scan_param.report_list),
            'report_name': str(scan_param.report_name),
            'dvh_file': str(scan_param.dvh_file),
            'save_file': str(scan_param.save_file),
            'plan_structures': str(scan_param.plan_structures),
            'match_table': str(scan_param.match_table)
            }

        param_text = 'Scan Parameters'
        param_text += '\n'.join(key +' = {' + key + '}'
                                for key in param_dict)
        param_text = param_text.format(**param_dict)
        return param_text

    def test_message(scan_param: PlanEvalParameters):
        '''Display a message box containing parameter info.
        '''
        message_text = param_string(scan_param)
        messagebox.showinfo(title='Parameters', message=message_text)

    test_scan_param = PlanEvalParameters(\
        base_path=Path(r'..\Test Data'),
        reports=['SABR 60 in 8', 'SABR 48 in 4'],
        save_file_name='SABR Plan Evaluation Worksheet Test Save.xls')
    activate_gui(test_scan_param, test_message)

if __name__ == '__main__':
    main()
