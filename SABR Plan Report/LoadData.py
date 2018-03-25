# -*- coding: utf-8 -*-
"""
Created on Sun Mar 18 16:07:52 2018

@author: Greg
"""

def load_items(file_path):
    '''Read in data from a comma separated text file.
    The first line of the file defines the variable names.
    All lines must have the same number of elements.
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
        row_dict = dict()
        for (key, value) in zip(variables, row_values):
            if value:
                row_dict[key] = value
        if row_dict:
            elements.append(row_dict)
    return elements
