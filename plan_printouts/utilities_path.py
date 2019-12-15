'''
Created on Mon Jan 10 2019

@author: Greg Salomons
Set the path to the Utilities Package.
'''
from pathlib import Path
import sys
# utilities_path = r"C:\Users\Greg\OneDrive - Queen's University\Python\Projects\Utilities"

current_path = Path.cwd()
projects_level = current_path.parts.index('Projects')
levels = list(current_path.parents)
levels.reverse()
project_path = levels[projects_level]
utilities_path = project_path / 'Utilities'
utilities_path_str = str(utilities_path.resolve())
sys.path.append(utilities_path_str)
