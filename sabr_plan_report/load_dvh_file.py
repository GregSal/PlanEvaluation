'''
Created on Sun Mar 18 21:37:14 2018

@author: Greg
Defines Classes and Methods related to reading plan data and extracting
elements for analysis.
'''


from pathlib import Path
import re
import logging
from plan_data import Plan


logging.basicConfig(level=logging.WARNING)
LOGGER = logging.getLogger(__name__)


def find_unit(text):
    '''Return a unit string and name from a text.
    Unit is surrounded by [].
    '''
    unit = None
    name = text
    marker1 = text.find('[')
    if marker1 != -1:
        marker2 = text.find(']', marker1)
        if marker2 != -1:
            unit = text[marker1+1:marker2]
            name = text[:marker1-1].strip()
    return name, unit


class DvhFile():
    '''Controls reading of a .dvh plan file.
    A subclass of io.TextIOBase with the following additional Attributes and
    Methods:
    Attributes:
        file_name:  type Path
            The full path to a the dvh file.
        file:
            A text file stream object created by open()
        last_line:  type str
            The line that has most recently been returned by a readline() call.
            This allows for a simple method to backup one line in the file.
        previous_postions: type int
            The previous file stream position, as defined by tell()
            It points to the beginning of the previous line.
            This allows for a method to backup one line in the file.
    Methods:
        __init__(file_name: Path **kwds):
            Open the file to begin reading.
        readline(previous=False)
            read a line from the dvh file.
            If previous=True, return last_line rather than reading a
            new line.
        backup(lines=1)
            Move the current stream position of file backwards by 'lines'
            number of lines.
    '''
    special_charaters = {'cm³': 'cc'}

    def __init__(self, file_name: Path, **kwds):
        '''Open the file_name file to begin reading.
        **kwds are passed as parameters to the Path.open method.
        Use utf_8 encoding by default.
        '''
        if not kwds.get('encoding'):
            kwds['encoding'] = 'utf_8'
        self.file = file_name.open(**kwds)
        self.file_name = file_name
        self.last_line = None
        self.do_previous = False

    def catch_special_char(self, raw_line: str):
        '''Convert line to ASCII.
        Look for special character strings in the line and replace with
        standard ASCII.
        Remove all other non ASCII characters.
        '''
        for (special_char, replacement) in self.special_charaters.items():
            if special_char in raw_line:
                patched_line = raw_line.replace(special_char, replacement)
            else:
                patched_line = raw_line
        bytes_line = patched_line.encode(encoding="ascii", errors="ignore")
        new_line = bytes_line.decode()
        return new_line

    def readline(self, **kwds):
        '''Read in the next line of text file, remembering previous line.
        '''
        if self.do_previous:
            new_line = self.last_line
            self.do_previous = False
        else:
            raw_line = self.file.readline(**kwds)
            new_line = self.catch_special_char(raw_line)
            self.last_line = new_line
        return new_line

    def backstep(self):
        '''Set the next call to self.readline to return last_line.
        '''
        self.do_previous = True

    def read_lines(self, break_cond=None):
        '''Iterate through lines of text data until the stop iteration
        condition is met.
        break_cond defines the stop iteration condition.
        Parameters:
            break_cond:
                A string to look for in the current text line to indicate the
                iteration should stop.
                If break_cond is None, iteration will stop at the beginning of
                the next blank line.
                If break_cond is a string, iteration will stop at the first
                occurrence of that string and the file pointer will be stepped
                back one line.
        Returns text_line: type str
        '''
        # Set stop iteration condition
        if break_cond is None:
            def test(line):
                '''one character for new line'''
                return len(line) > 1
        else:
            def test(line):
                '''check for break_cond.'''
                return break_cond not in line
        # Read file lines until stop iteration condition is met
        text_line = self.readline()
        while test(text_line):
            yield text_line
            text_line = self.readline()
        # Move back one line in file
        self.backstep()

    def read_data_elements(self, break_cond=None):
        '''Iterate through lines of text data and returning the resulting
        element parameters extracted from each line.
        break_cond is passed through to read_lines.
            If break_cond is None, iteration will stop at the next blank line.
            If break_cond is a string, iteration will stop at the first
            occurrence of that string and the file pointer will be stepped
            back one line.
        Returns parameters
        '''
        def parse_element(text_line: str):
            '''convert a line of text into PlanElement parameters.
            '''
            line_element = text_line.split(':', 1)
            (item_name, item_unit) = find_unit(line_element[0].strip())
            parameters = {'name': item_name,
                          'unit': item_unit,
                          'element_value': line_element[1].strip()}
            return parameters

        for text_line in self.read_lines(break_cond):
            if ':' in text_line:
                yield parse_element(text_line)

    def load_dvh(self):
        '''Load a DVH table from a .dvh file.
        '''
        def parse_line(text):
            '''Split line into multiple numbers.
            '''
            return [float(num) for num in text.split()]

        def make_column_list(dvh_header):
            '''Build a list of DVH column identifiers.
            '''
            columns = list()
            for (name, unit) in dvh_header:
                column_name = name.strip().lower()
                column_unit = unit.strip()
                if 'dose' in column_name:
                    columns.append({'Data Type': 'Dose',
                                    'Unit': column_unit})
                elif 'volume' in column_name:
                    columns.append({'Data Type': 'Volume',
                                    'Unit': column_unit})
                else:
                    columns.append({'Data Type': column_name,
                                    'Unit': column_unit})
            return columns

        text_line = self.readline()
        dvh_header_pattern = (
            "([^\[]+)[\[]"  # everything until '[' # pylint: disable=anomalous-backslash-in-string
            "([^\]]+)[\]]"  # everything inside the  [] # pylint: disable=anomalous-backslash-in-string
            )
        re_dvh_header = re.compile(dvh_header_pattern)
        dvh_header = re_dvh_header.findall(text_line)
        columns = make_column_list(dvh_header)
        dvh_list = [parse_line(text) for text in self.read_lines()]
        return {'dvh_columns': columns, 'dvh_list': dvh_list}

    def load_structure(self):
        '''Load data for a single structure from a .dvh file.
        '''
        structure_data = {'properties_list':
                          [props for props in self.read_data_elements()]}
        self.readline()  # Skip blank line
        structure_data.update(self.load_dvh())
        return structure_data

    def load_structures(self):
        '''Loads all structures in a file.
        Returns a dictionary of structures with the structure name as key.
        '''
        text_line = self.readline()
        while text_line:
            if ':' in text_line:
                structure_data = {'name': text_line.split(':', 1)[1].strip()}
                structure_data.update(self.load_structure())
                yield structure_data
            text_line = self.readline()

    def load_data(self):
        '''Load data from the .dvh file.
        '''
        plan_parameters = [parameters for parameters in
                           self.read_data_elements('Structure')]
        plan_structures = [structure_data for structure_data in
                           self.load_structures()]
        return (plan_parameters, plan_structures)

def main():
    '''Test
    '''
    plan_file_name = Path(r"..\Test Data\DVH Test Data.dvh")
    plan_file = DvhFile(plan_file_name)
    test_plan = Plan('test1', plan_file_name)
    (plan_parameters, plan_structures) = plan_file.load_data()
    for parameters in plan_parameters:
        test_plan.add_plan_property(parameters)
    for structure_data in plan_structures:
        test_plan.add_structure(**structure_data)
    print(test_plan)

if __name__ == '__main__':
    main()
