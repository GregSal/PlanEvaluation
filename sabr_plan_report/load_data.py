"""
Created on Sun Mar 18 16:07:52 2018

@author: Greg
"""


def load_items(file_path):
    '''Read in data from a comma separated text file.
    The first line of the file defines the variable names.
    If a line has more elements than the number of variables then the last
    variable is assigned a list of trhe remaining elements.
        Parameters:
            file_path: type Path
                The path to the text file containing the comma separated values
            Returns:
                element_list: list of dictionaries
                    keys are the variable names
                    values are the values on a given row.
                    No type checking is done.
    '''
    file_contents = file_path.read_text().splitlines()
    variables = file_contents.pop(0).strip().split(',')
    elements = []
    for text_line in file_contents:
        row_values = text_line.strip().split(',')
        row_dict = {key: value
                    for (key, value) in zip(variables, row_values)
                    if value}
        if len(row_values) > len(variables):
            row_dict[variables[-1]] = row_values[len(variables)-1:]
        if row_dict:
            elements.append(row_dict)
    return elements
