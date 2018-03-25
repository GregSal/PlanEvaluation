'''
Created on Sun Mar 18 21:37:14 2018

@author: Greg
Defines Classes and Methods related to reading plan data and extracting
elements for analysis.
'''


from pathlib import Path
import re
import logging
from PlanData import Plan


logging.basicConfig(level=logging.DEBUG)
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


class DVH_File():
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
        previous_postions: type list
            A list of the file stream positions, as defined by tell(), pointing to
            the beginning of the previous lines.
            This allows for a method to backup multiple lines in the file.
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
        self.previous_postions = [0, ]

    def readline(self, do_previous=False, **kwds):
        '''Read in the next line of text file, remembering previous line.
        '''
        if do_previous:
            new_line = self.last_line
        else:
            new_line = self.file.readline(**kwds)
            self.previous_postions.append(self.file.tell())
            self.last_line = new_line
        return new_line

    def backstep(self, lines=1):
        '''Move the current stream position of file backwards by 'lines' number
        of lines.
        '''
        offset = -lines - 1
        set_position = self.previous_postions[offset]
        self.file.seek(set_position)
        self.previous_postions = self.previous_postions[:offset+1]

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
        for text_line in self.read_lines(break_cond):
            if ':' in text_line:
                yield self.parse_element(text_line)

    def parse_element(self, text_line: str):
        '''convert a line of text into PlanElement parameters.
        '''
        line_element = text_line.split(':', 1)
        (item_name, item_unit) = find_unit(line_element[0].strip())
        parameters = {'name': item_name,
                      'unit': item_unit,
                      'element_value': line_element[1].strip()}
        return parameters

    def load_dvh(self):
        '''Load a DVH table from a .dvh file.
        '''
        def parse_line(text):
            '''Split line into multiple numbers.
            '''
            return [float(num) for num in text.split()]

        text_line = self.readline()
        dvh_header_pattern = (
            "([^\[]+)[\[]"  # everything until '['
            "([^\]]+)[\]]"  # everything inside the  []
            )
        re_dvh_header = re.compile(dvh_header_pattern)
        dvh_header = re_dvh_header.findall(text_line)
        columns = [{'name': n.strip(), 'unit': u.strip()} for (n, u) in dvh_header]
        dvh_list = [parse_line(text) for text in self.read_lines()]
        return {'columns': columns, 'dvh_list': dvh_list}

    def load_structure(self):
        '''Load data for a single structure from a .dvh file.
        '''
        properties_list = [props for props in self.read_data_elements()]
        self.readline()  # Skip blank line
        dose_data = self.load_dvh()
        return (properties_list, dose_data)

    def load_structures(self):
        '''Loads all structures in a file.
        Returns a dictionary of structures with the structure name as key.
        '''
        text_line = self.readline()
        while text_line:
            if ':' in text_line:
                structure_name = text_line.split(':', 1)[1].strip()
                structure_values = self.load_structure()
                yield (structure_name, *structure_values)
            text_line = self.readline()

    def load_data(self, plan):
        '''Load data from the .dvh file.
        '''
        for parameters in self.read_data_elements('Structure'):
            plan.add_plan_property(parameters)
        for structure_data in self.load_structures():
            plan.add_structure(*structure_data)

def main():
    '''Test
    '''
    plan_file_name = Path(r"..\Test Data\DVH Test Data.dvh")
    plan_file = DVH_File(plan_file_name)
    test_plan = Plan('test1', plan_file_name)
    plan_file.load_data(test_plan)
    print(test_plan)

if __name__ == '__main__':
    main()
