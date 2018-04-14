'''
Created on Aug 11 2017

@author: Greg Salomons
Define parameters required for plan evaluation.

Warnings
    NameInUse:
        An output file or sheet name is already in use.
    InvalidPath:
        The given path is not a valid selection.
Exceptions
    NameInUse:
        An output file or sheet name is already in use.
    InvalidPath:
        The given path is not a valid selection.
    FileTypeError:
        The file extension is not the appropriate type.
    SelectionError:
        The string contents are not valid.
Classes
    PlanEvalParameters:  Input parameters required for plan evaluation.

Functions
    valid_dir:
        Convert string to path if required, check that the path is an
        existing directory and return the full path.
    valid_file:
        Convert string to path if required, check that the path is an
        exiting file and return the full path.
    valid_sheet_name
        Check that the supplied sheet_name is valid.
'''
from pathlib import Path
# import warnings


#Warning and Exception definitions
class NameInUse(UserWarning):
    '''An output file or sheet name is already in use.
    '''
    pass
class InvalidPath(UserWarning):
    '''The given path is not a valid selection.
    '''
    pass
class FileTypeError(FileNotFoundError):
    '''The file extension is not the appropriate type.
    '''
    pass
class SelectionError(TypeError):
    '''The string contents are not valid.
    '''
    pass


# Methods to check directories, files and sheet names
def valid_dir(dir_path: Path):
    ''' If dir_path is a string convert it to type Path.
        Resolve any relative path parts.
        Check that the supplied path exists and is a directory.
    Parameter
        dir_path: Type Path or str
            a relative or full path to a directory
    Returns
        A full path to an existing directory of type Path
    Raises
        TypeError exception
        NotADirectoryError exception
    '''
    if isinstance(dir_path, Path):
        full_directory_path = dir_path.resolve()
    elif isinstance(dir_path, str):
        full_directory_path = Path(dir_path).resolve()
    else:
        raise TypeError('The directory path must be Type Path or str')
    if full_directory_path.is_dir():
        return full_directory_path
    else:
        raise NotADirectoryError(\
            'The directory path must refer to an existing directory')

def valid_file(file_path: Path):
    ''' If file_path is a string convert it to type Path.
        Resolve any relative path parts.
        Check that the supplied path exists and is a file.
    Parameter
        file_path: Type Path or str
            a relative or full path to a file
    Returns
        A full path to an existing file of type Path
    Raises
        TypeError exception
        FileNotFoundError exception
    '''
    if isinstance(file_path, Path):
        full_file_path = file_path.resolve()
    elif isinstance(file_path, str):
        full_file_path = Path(file_path).resolve()
    else:
        raise TypeError('The file path must be Type Path or str')
    if full_file_path.exists():
        return full_file_path
    else:
        msg = 'The file path must refer to an existing file'
        raise FileNotFoundError(msg)

def valid_sheet_name(sheet_name: str):
    ''' Check that the supplied sheet_name is valid.
    Parameter
        sheet_name: Type str
            An excel worksheet name.
    Returns
        A full path to an existing file of type Path
    Raises
        TypeError exception
    '''
    if not isinstance(sheet_name, str):
        raise TypeError('The sheet name must be Type str')
    else:
        #ToDo Add legal worksheet name tests
        return True


# Principal class definition
class PlanEvalParameters(object):
    '''Contains all parameters required for reporting plan evaluation.
    Class Attributes:
        base_path
            Type: Path
            The starting path to use for incomplete file and directory
            parameters
            Default = Path.cwd()

    The following Class-level attributes are currently not updated directly:
        report_definition_file
            Type: Path
            The path to the report definition file

    Instance Attributes:
        report_list
            Type: list of str
            A list of the names of the possible plan reports
            Default = empty list
        report_name
            Type: String
            The name of the plan report to use
            Default = empty string
        dvh_file
            Type: Path
            The path to a file containing the DVH table output from the plan
            to be evaluated.
            The file must exists and the extension must be ".dvh"
            Default = base_path / 'dvh_table.dvh'
        save_file
            Type: Path
            The excel file name where the completed plan report will be saved.
            The file extension must be either ".xls" or ".xlsx"
            Default = base_path / "plan report.xls"
        plan_structures
             Type: list of str
             The names of the structures found in the plan DVH file
            Default = empty list
        match_table
            Type: dictionary,
                key: report element name,
                value: tuple of (plan element type, plan element name)
            a table of report elements and matched plan elements
            Default = empty dictionary

    Methods
        __init__
			Set attributes
			Verify that attributes are reasonable
        The following methods are used to test or modify passed parameters
            add_base_path(self, file_name: str)
            is_output_collision(self)
        The following methods are used to check and update parameters
            update_report_list(self, report_list)
            update_report_name(self, report_name)
            update_dvh_file(self, file_path)
            update_plan_structures(self, structures_list)
            update_match_table(self, initial_match)
            update_match_item(self, report_element_name,
                                plan_element_type, plan_element_name,
                                manual_value=None)
    '''
	# Initialize class level parameters
    base_path = Path.cwd()
    report_definition_file = Path.cwd()

    #The following method initializes parameters
    def __init__(self, base_path=None, **kwargs):
        '''
        Initialize all parameters, using default values if a value is
        not supplied
        '''
		# Initialize all parameters, using default values
        self.report_name = ''
        self.dvh_file = None
        self.save_file = None
        self.plan_structures = list()
        self.match_table = dict()

        if base_path is not None:
            self.update_base_path(base_path)
            # Set passed parameters using defined method
        for item in kwargs:
            if hasattr(self, 'update_' + item):
                set_method = getattr(self, 'update_' + item)
                set_method(kwargs[item])


    #The following methods are used to test or modify passed parameters
    def insert_base_path(self, file_name: str):
        '''Add the base path to a filename or relative string path.
        Check for presence of ':' or './' as indications that file_name is
            a full or relative path. Otherwise assume that file_name is a
            name or partial path to a file or directory.
        Parameter
            file_name: Type str
                a name or partial path to a file or directory
        Returns
            A full path to a file or directory of type Path
        Raises
            TypeError exception
        '''
        if isinstance(file_name, Path):
            try:
                full_path = file_name.resolve()
            except PermissionError:
                full_path = file_name
            return full_path
        elif isinstance(file_name, str):
            if any(a in file_name for a in[':', './']):
                try:
                    full_path = Path(file_name).resolve()
                except PermissionError:
                    full_path = Path(file_name)
                return full_path
            full_path = self.base_path / file_name
            return full_path
        raise TypeError('file_name must be Type Path or str')

    #The following methods are used to check and update parameters
    def update_base_path(self, directory_path: Path):
        ''' Update the base path.
        directory_path must exist and be a directory.
        directory_path must be of type Path.
        Parameter
            directory_path: Type Path
                The path to be used to complete any file name or partial
                paths
        Raises
            TypeError exception
        '''
        if not isinstance(directory_path, Path):
            raise TypeError('directory_path must be Type Path')
        full_directory_path = valid_dir(directory_path)
        self.base_path = full_directory_path

    def update_dvh_file(self, file_path):
        ''' Update the name of the text file containing the DVH table output
        from the plan to be evaluated.
        Parameter
            file_path: Type Path
                The file containing scan results to be parsed.
        Raises
            FileTypeError exception
        If file_path is a string treat it as a partial and combine it with
        the base path.
        The file must exist and the extension must be ".dvh"
        '''
        # If file_path is a string treat it as a partial and combine it
        # with the base path
        dvh_file = valid_file(self.insert_base_path(file_path))
        if 'dvh' in dvh_file.suffix:
            self.dvh_file = dvh_file
        else:
            raise FileTypeError('The DVH file must be of type ".dvh"')

    def update_save_file(self, file_path):
        ''' Update the name of the excel file name where the completed plan
        report will be saved.
        The file extension must be either ".xls" or ".xlsx".
        Parameter
            file_path: Type str
                A name or partial path to a file for saving the excel plan report.
        Raises
            FileTypeError
            NameInUse
        If file_path is a string treat it as a partial and combine it with
        the base path.
        The file extension must be either ".xls" or ".xlsx"
        '''
        # If directory_path is a string treat it as a partial and combine it
        # with the base path
        output_file = self.insert_base_path(file_path)
        if output_file.suffix not in ['.xls', '.xlsx']:
            msg = 'Output file must be of type ".xls" or ".xlsx"'
            raise FileTypeError(msg)
        else:
            self.save_file = output_file

    def update_report_name(self, name: str):
        '''Change the selected report name to name.
        '''
        self.report_name = name

    def update_report_list(self, report_list: list):
        '''Change the selected report name to name.
        '''
        self.report_list = report_list

    def update_plan_structures(self, structures_list: list):
        '''Append the supplied list of structure names to plan_structures.
        '''
        self.plan_structures.extend(list(structures_list))

    def update_match_table(self, matches: dict):
        '''Append the supplied list of matched elements to match_table.
        '''
        self.match_table.update(matches)

def main():
    '''Test the Parameters class definition
    '''
    base_path = Path(r'..\Test Data')
    reports = ['SABR 60 in 8', 'SABR 48 in 4']
    save_file_name = 'SABR Plan Evaluation Worksheet Test Save.xls'
    test_parameters = \
        PlanEvalParameters(base_path, report_list=reports, save_file=save_file_name)
    print(test_parameters)

if __name__ == '__main__':
    main()
