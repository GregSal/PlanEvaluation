'''
Created on Sun Mar 18 21:37:14 2018

@author: Greg
Defines Classes and Methods related to reading plan data and extracting
elements for analysis.
'''


from pathlib import Path
import logging
import re
from scipy.interpolate import interp1d
import numpy as np
import xml.etree.ElementTree as ET


logging.basicConfig(level=logging.WARNING)
LOGGER = logging.getLogger(__name__)


def get_laterality_exceptions(region_code_root):
    region_code_list = list()
    for element in region_code_root.findall('BodyRegion'):
        region_code = element.attrib.get('Name')
        region_code_list.append(region_code)
    return region_code_list


def get_default_units(config: ET.Element):
    '''Sets the default units for the plan data.
    Parameters
        One or more of the following:
                DoseUnit: One of ('Gy', 'cGy', '%')
                VolumeUnit: One of ('cc', '%')
                DistanceUnit: 'cm')
    '''
    default_units_settings = dict()
    for default_unit in config.findall(r'./PlanDefaults/*'):
        unit_type = default_unit.tag
        unit = default_unit.text
        default_units_settings[unit_type] = unit
    return default_units_settings


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


def convert_units(starting_value, starting_units, target_units,
                  dose=1.0, volume=1.0):
    '''Take value in starting_units and convert to target_units.
    '''
    conversion_table = {'cGy': {'cGy': 1.0, '%': 100/dose, 'Gy': 0.01},
                        'Gy':  {'Gy': 1.0, '%': 1.0/dose, 'cGy': 100},
                        'cc':  {'cc': 1.0, '%': 100/volume},
                        '%':   {'%': 1.0,
                                'cGy': dose/100.0,
                                'Gy': dose,
                                'cc': volume/100}
                       }
    conversion_factor = conversion_table[starting_units][target_units]
    new_value = float(starting_value)*conversion_factor
    return new_value


class PlanElement():
    '''A single value item for the plan.  e.g.: 'Normalization'.
        Defines the name, value_type, unit and value attributes.
    Attributes:
        name: type str
            The name of the PlanElement instance.
        element_value:  type depends on value_type
            The numeric or text value of the property
        unit: type str
            Defines the units of the PlanProperty value. Valid options depend
            on value_type.  Possible values are:
                ('%', 'Gy', 'cGy', 'cc', 'cm', 'N/A')
    Methods
        __init__(self, name=None, **parameter_values)
        define(self, element_value=None, unit=None)
        get_value(self, unit=None, conversion_method=None)
        __repr__(self)
        __bool__(self)
    '''
    def __init__(self, name=None, element_value=None, unit=None):
        '''Initialize the base properties of all PlanElements.
        If name is not supplied, return an object with self.name = None as the
        only attribute.
        '''
        self.name = str(name)
        self.unit = None
        self.value = None
        self.define(element_value, unit)

    def define(self, element_value=None, unit=None):
        '''Set Element Attributes.
        '''
        try:
            self.element_value = float(element_value)
        except (ValueError, TypeError):
            self.element_value = element_value
        if unit:
            self.unit = str(unit)
        else:
            self.unit = unit
        pass

    def get_value(self, constructor='', **conversion_parameters):
        '''Returns the requested value in the desired units.
        '''
        # TODO constructor can be regular expression to derive custom string values e.g. site from Plan Name
        initial_value = self.element_value
        initial_unit = self.unit
        if initial_value and initial_unit:
            final_value = convert_units(initial_value, initial_unit,
                                        **conversion_parameters)
        else:
            final_value = initial_value
        return final_value

    def __bool__(self):
        '''Indicate empty Element.
        Return my truth value (True or False).
        '''
        return bool(self.name)

    def __repr__(self):
        '''Describe a Plan Element.
        '''
        attr_str = 'name={}'.format(self.name)
        if self.unit:
            attr_str += ', unit={}'.format(self.unit)
        if self.element_value:
            attr_str += ', element_value={}'.format(self.element_value)
        return 'PlanElement(' + attr_str + ')'


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


class DVH():
    '''DVH dose data for a given structure.
    Attributes:
        dvh_columns:  type list of dictionaries
            Each element of the list is a dictionary corresponding to one
            column of data.
            The dictionary contains the following elements:
                name: the name of the data column
                unit: units defined for the column
        dvh_curve
            A 3xN array of Dose and Volume
    Methods:
        load_dvh_curve
            parse DVH data read in from the plan file
        get_dvh_value(constructor, unit=None)
            extract a specific dose or volume value.
            Returns the value in the requested units.
            If unit is None, returns the value in the default units defined
            with set_units.
    '''
    def __init__(self, columns=None, dvh_curve=None):
        '''Initialize a DVH data set.
        '''
        self.dvh_columns = columns
        self.dvh_curve = np.array(dvh_curve).T

    def select_columns(self, x_unit, y_type, y_unit=None):
        '''Select the appropriate x and y DVH columns.
        '''
        x_column = y_column = x_possible = y_possible = None
        desired_x_unit = None
        for(index, column) in enumerate(self.dvh_columns):
            if y_type in column['Data Type']:
                y_possible = index
                if y_unit and (y_unit in column['Unit']):
                    y_column = index
            else:
                x_possible = index
                if x_unit in column['Unit']:
                    x_column = index
                    desired_x_unit = None
                else:
                    desired_x_unit = column['Unit']
        if not x_column:
            x_column = x_possible
        if not y_column:
            y_column = y_possible
        return x_column, y_column, desired_x_unit

    def get_dvh_point(self, x_column, y_column, x_value):
        '''Interpolate DVH curve to select a value.
        '''
        data = self.dvh_curve
        if min(data[x_column]) < float(x_value) < max(data[x_column]):
            linear_interp = interp1d(data[x_column], data[y_column])
            target_value = float(linear_interp(x_value))
        else:
            target_value = None
        return target_value

    def get_value(self, dvh_constructor=None, **conversion_parameters):
        '''Return the value in the requested units.
        '''
        (y_type, x_value, x_unit) = dvh_constructor
        (x_column, y_column, desired_x_unit) = \
            self.select_columns(x_unit, y_type)
        if desired_x_unit:
            x_value = convert_units(float(x_value), x_unit,
                                    target_units=desired_x_unit,
                                    **conversion_parameters)
        dvh_value = self.get_dvh_point(x_column, y_column, x_value)
        dvh_unit = self.dvh_columns[y_column]['Unit']
        dvh_name = ''.join(dvh_constructor)
        dvh_point = PlanElement(name=dvh_name,
                                element_value=dvh_value,
                                unit=dvh_unit)
        return dvh_point


class Structure():
    '''Plan data associated with a particular structure.
    Attributes:
        properties type dict
            A dictionary of structure properties of a PlanElement sub-type.
        dose_data type DVH
            The DVH data associated with the structure.
    Methods:
        load_structure
            parse structure data read in from the plan file
        get_laterality
            Determine laterality, if any of the structure from the plan data.
            Store laterality in properties as a PlanElement.
        get_volume
            Determine the volume of the structure from the plan data.
            Store volume in properties as a PlanElement.
        laterality
            Returns the structures laterality
        volume
            Returns the structures volume
    '''
    def __init__(self, name=None, **properties):
        '''Initialize a structure.
        Parameters:
            name:  type str
                The name of the structure
            unit_conversion:  type callable
                function to convert units.
            properties:  type list
                contains a list of dictionaries of structure properties
        '''
        if name:
            self.name = str(name)
            self.structure_properties = dict()
            self.dose_data = None
            self.define(**properties)
        else:
            self.name = None

    def define(self, dvh_columns=None, dvh_list=None, properties_list=None):
        '''Set Element Attributes.
            dvh_columns, dvh_list:
                Passed to DVH to generate DVH data.
            properties_list:  type list
                contains a list of dictionaries of structure properties
        '''
        if properties_list:
            for element_properties in properties_list:
                element = PlanElement(**element_properties)
                self.structure_properties[element.name] = element
        self.dose_data = DVH(columns=dvh_columns, dvh_curve=dvh_list)

    def get_value(self, constructor='', **conversion):
        '''Return the value in the requested units.
        '''
        def parse_constructor(constructor):
            '''Parse the element constructor for reference to a DVH point.
            DVH point constructors take the form:
                one of D or V - representing Dose or Volume as the y axis
                a number (either float or integer) to look up on the x axis
                the units of the number as a text string
            returns a three-element tuple if a point constructor was found
            returns None otherwise
            '''
            re_construct = re.compile(
                r'^(?P<target>[DV])\s?'  # Target type: D for dose of V for volume
                r'(?P<value>\d+\.?\d)\s?'  # Search value a decimal or integer
                r'(?P<unit>[\w%]+)$'           # Units of search value
                )
            dvh_constructor = re_construct.findall(constructor)
            return dvh_constructor

        volume_property = self.structure_properties.get('Volume')
        if volume_property:
            conversion['volume'] = volume_property.element_value
        else:
            conversion['volume'] = 1.0
        dvh_constructor = parse_constructor(constructor)
        if dvh_constructor:
            element = self.dose_data.get_value(dvh_constructor[0])
        else:
            element = self.structure_properties.get(constructor)
        if element:
            value = element.get_value(**conversion)
        else:
            value = None
        return value

    def __bool__(self):
        '''Indicate empty Structure.
        Return my truth value (True or False).'''
        return bool(self.name)

    def __repr__(self):
        '''Describe a Structure.
        '''
        # Start with base attributes of a structure
        attr_str = 'name={}'.format(self.name)
        # Indicate the number of properties defined
        if self.structure_properties:
            properties_str = \
                'Contains {} properties'.format(
                    len(self.structure_properties))
        else:
            properties_str = ''
        # Indicate id DVH is defined
        if self.dose_data:
            dose_data_str = 'Contains DVH'
        else:
            dose_data_str = ''
        repr_string = '< Type Structure(' + attr_str + ')' + properties_str +\
            dose_data_str
        return repr_string


class Plan():
    '''Contains all plan elements for a single plan.
    Class Attributes:
        default_units:  type dict
             The default units for plan elements.
             Key-Value pairs are:
                 'DoseUnit': One of ('Gy', 'cGy', '%')
                 'VolumeUnit': One of ('cc', '%')
                 'DistanceUnit': 'cm')
    Instance Attributes:
        data_source:  type Path
            The path to a file containing the plan data.
        self.data_elements   type dict
            Contains all of the different categories of plan data items as
            keys.
            The categories are:
                'Plan Property':
                    A dictionary of plan properties of a PlanElement sub-type.
                'Structure':
                    A dictionary of plan elements of type Structure.
                'Reference Point'
                    A dictionary of plan elements of type ReferencePoint.
        prescription_dose:  type PlanElement
            The prescribed dose for the plan in the default units.
            It is used for converting dose units of other PlanElements.
    Methods
        __init__
            Define the plan data source
        set_units
            Sets the default units for the plan data.
        load_plan
            Read in data from the plan file
        get_laterality
            Determine laterality, if any of the plan from the plan data.
            Store laterality in plan_properties as a PlanElement.
        get_identifiers
            Extract key plan identifiers from the plan data.
            Store identifiers in plan_properties as multiple PlanElements.
        get_prescription
            Extract plan prescription from the plan data.
            Store Dose, Fractions, DosePerFraction in plan_properties.
        get_info
            Prompt for required, additional identifiers
        dose
            returns the prescription dose in the requested units
        fractions
            returns the number of fractions in the prescription.
    '''
    def __init__(self, name, config: ET.Element, dvh_file_name: str):
        '''Define the path to the file containing the plan data.
        '''
        self.name = str(name)
        dvh_path = Path(config.findtext(r'./DefaultDirectories/DVH'))
        dvh_file = dvh_path / dvh_file_name
        data_source = DvhFile(dvh_file)
        self.data_source = Path(data_source.file_name) #Plan.data_source appears redundant
        self.default_units = get_default_units(config)
        self.data_elements = {'Plan Property': dict(),
                              'Structure': dict(),
                              'Reference Point': dict()}
        (plan_parameters, plan_structures) = data_source.load_data()
        self.add_plan_data(plan_parameters, plan_structures)

        code_exceptions_def = config.find('LateralityCodeExceptions')
        laterality_exceptions = get_laterality_exceptions(code_exceptions_def)
        self.laterality = self.get_laterality(laterality_exceptions)
        self.prescription_dose = self.set_prescription()

    def add_data_item(self, element_category, element):
        '''Add a PlanElement as a new plan property.
        '''
        element_entry = {element.name: element}
        self.data_elements[element_category].update(element_entry)
        LOGGER.debug('Created %s: %s', element_category, element.name)

    def add_plan_data(self, plan_parameters, structure_data_sets):
        '''Insert supplied plan parameters and structure data.
        Build a unit conversion for the plan based on the prescription dose.
        '''
        for parameters in plan_parameters:
            element = PlanElement(**parameters)
            self.add_data_item('Plan Property', element)
        for structure_data in structure_data_sets:
            structure = Structure(**structure_data)
            self.add_data_item('Structure', structure)

    def get_data_element(self, data_type, element_name):
        '''Return the PlanElement of type property_type with property_name.
        '''
        data_group = self.data_elements.get(data_type)
        element = data_group.get(element_name) if data_group else None
        return element

    def get_laterality(self, laterality_exceptions):
        '''Look for laterality indicator in plan name and use to set
        laterality modifier.
        '''
        # TODO need to deal with BOOS plan names
        laterality_options = {'R': 'Right',
                              'L': 'Left',
                              'B': 'Both'}
        plan_name = self.get_data_element(
            data_type='Plan Property',
            element_name='Plan')
        body_region = plan_name.element_value[0:3]
        if body_region in laterality_exceptions:
            return None
        laterality_code = plan_name.element_value[3]
        return laterality_options.get(laterality_code, None)

    def set_prescription(self):
        '''Sets the prescription dose in the default units to enable unit
        conversion for other elements.
        Calls get_value(source) method of PlanElement, Structure or
        ReferencePoint.
        '''
        dose = self.get_data_element(data_type='Plan Property',
                                     element_name='Prescribed dose')
        dose_value = dose.element_value
        desired_units = self.default_units['DoseUnit']
        if dose.unit != desired_units:
            dose_value = convert_units(dose_value, dose.unit,
                                       desired_units)
        return PlanElement(name='prescription_dose',
                           element_value=dose_value,
                           unit=desired_units)

    def __repr__(self):
        '''Describe a Plan.
        '''
        # Start with name and path to plan
        attr_str = 'Plan name = {}\nPlan file = {}\n'.format(
            self.name, self.data_source)
        # Indicate the number of properties defined
        properties_str = ''
        for (name, element_set) in self.data_elements.items():
            if element_set:
                properties_str += 'Contains {} {} elements.\n'.format(
                    len(element_set), name)
        repr_string = '< Type Plan(' + attr_str + ')>' + properties_str
        return repr_string
