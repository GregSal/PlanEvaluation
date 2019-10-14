'''
Created on Sun Mar 18 21:37:14 2018

@author: Greg
Defines Classes and Methods related to reading plan data and extracting
elements for analysis.
'''


from typing import Union, NamedTuple, Tuple, Dict, List, Any
from pathlib import Path
import xml.etree.ElementTree as ET
import re
import logging
import numpy as np
from scipy.interpolate import interp1d


Value = Union[int, float, str]
ConversionParameters = Dict[str, Union[str, float, None]]
ColumnDef = Dict[str, str] # 2 items: 'Data Type','Unit'
# TODO Make ColumnDef a named tuple
Header = List[ColumnDef]
DvhData = List[List[float]]
# number of items in List[float] = number of items in List[ColumnDef]
# TODO Make DvhConstructor a named tuple
DvhConstructor = Tuple[str, float, str] # (y_type, x_value, x_unit)
# TODO Make DvhIndex a named tuple
DvhIndex = Tuple[int, int, str]
#x_column, y_column, desired_x_unit

LOGGER = logging.getLogger(__name__)


class PlanDescription(NamedTuple):
    '''Summary info for a Plan file.
    Attributes:
        plan_file {Path} -- The full path to the plan file.
        file_type {str} -- The type of plan file. Currently only "DVH".
        patient_name {str} -- The full name of the patient.
        patient_id {str} -- The ID assigned to the patient (CR#).
        plan_name {str} -- The plan ID, or name.
        course {optional, str} -- The course ID.
        dose {optional, float} -- The prescribed dose in cGy.
        fractions {optional, int} -- The number of fractions.
        export_date {optional, str} -- The date, as a string, when the plan
            file was exported.
    '''
    plan_file: Path
    file_type: str
    patient_name: str
    patient_id: str
    plan_name: str
    course: str = None
    dose: float = None
    fractions: int = None
    export_date: str = None


def get_laterality_exceptions(region_code_root: ET.Element)->List[str]:
    '''Load list of body region codes that appear to have a laterality,
        but do not.
    Arguments:
        region_code_root {ET.Element} -- An XML element containing a series of
            body region codes that end in "L", "R" or "B", where the letter
            does not indicate laterality. e.e "ORAL".
    Returns:
        List[str] -- a list of 4-letter body region codes which should not be
            treated as indicating laterality in the plan.
    '''
    region_code_list = list()
    for element in region_code_root.findall('BodyRegion'):
        region_code = element.attrib.get('Name')
        region_code_list.append(region_code)
    return region_code_list


def get_default_units(config: ET.Element)->Dict[str, str]:
    '''Sets the default units for the plan data.
    Arguments:
        config {ET.Element} -- An XML element containing a series of
            default units for plan values.
    Returns:
        Dict[str, str] -- A dictionary listing unit types and the corresponding
            default unit. Contains one or more of the following:
                DoseUnit: One of ('Gy', 'cGy', '%')
                VolumeUnit: One of ('cc', '%')
                DistanceUnit: ('mm', 'cm')
    '''
    default_units_settings = dict()
    for default_unit in config.findall(r'./PlanDefaults/*'):
        unit_type = default_unit.tag
        unit = default_unit.text
        default_units_settings[unit_type] = unit
    return default_units_settings


def convert_units(starting_value: Value, starting_units: str, target_units: str,
                  dose: float = None, volume: float = None)->float:
    '''Take value in starting_units and convert to target_units.
    Arguments:
        starting_value {Value} -- The initial numerical value. If
            starting_value is a string try to convert it to a float. If
            conversion is not successful raise ValueError.
        starting_units {str} -- The initial units of starting_value. Must
            match a key in the conversion table.
        target_units {str} -- The unit to convert starting_value to. Must
            be of the same unit type as starting_units.
    Keyword Arguments:
        dose {float} -- The reference dose value to use for % dose conversions.
          Default is None. (This will raise an error if dose % conversion is
          attempted without supplying a reference dose.)
        volume {float} -- The reference volume value to use for % volume
            conversions. Default is None. (This will raise an error if % volume
            conversion is attempted without supplying a reference dose.)
    Returns:
        float -- The initial value converted to the new units.
    '''
    # TODO Move the conversion_table to the config XML file.
    # Make it easier to add new unit types.
    # TODO re-consider "Value" class that contains number and unit.
    # convert_units would become a method of the Value" class.
    # find_unit and get_default_units could also become part of Value
    # constructors.  Config could contain different text parsing definitions
    # that would extract name, value and units.
    conversion_table = {'cGy': {'cGy': 1.0,
                                '%': 100/dose if dose else None,
                                'Gy': 0.01
                                },
                        'Gy':  {'Gy': 1.0,
                                '%': 1.0/dose if dose else None,
                                'cGy': 100},
                        'cc':  {'cc': 1.0,
                                '%': 100/volume if volume else None
                                },
                        '%':   {'%': 1.0,
                                'cGy': dose/100.0 if dose else None,
                                'Gy': dose if dose else None,
                                'cc': volume/100 if volume else None
                                }
                       }
    try:
        conversion_factor = conversion_table[starting_units][target_units]
    except KeyError as err:
        raise ValueError('Unknown units') from err
    new_value = float(starting_value)*conversion_factor
    return new_value

# Question consider a Constructor class
# constructor would take a plan element as argument and return a value.
# This requires some thinking.  it is not straight forward.
def parse_constructor(constructor: str)->DvhConstructor:
    '''Parse the element constructor for reference to a DVH point.
    Arguments:
        constructor {str} -- A DVH point constructor with the form:
            One of D or V - representing Dose or Volume as the y-axis
            A number (either float or integer) to look up on the x-axis
            The units of the number as a text string
    Returns:
        DvhConstructor -- If a point constructor was found:
            A tuple of the form:
                ([D or V], [x-axis value], [units of the x-axis value])
            None otherwise.
    '''
    re_construct = re.compile(
        r'^(?P<target>[DV])\s?'  # Target type: D for dose of V for volume
        r'(?P<value>\d+\.?\d)\s?'  # Search value a decimal or integer
        r'(?P<unit>[\w%]+)$'           # Units of search value
        )
    dvh_constructor = re_construct.findall(constructor)
    if dvh_constructor:
        dvh_constructor = dvh_constructor[0]
    else:
        dvh_constructor = None
    return dvh_constructor


class PlanDataItem():
    '''A single value item for the plan.  e.g.: 'Normalization'.
        Defines the name, value_type, unit and value attributes.
    Arguments:
        name {str} -- The name of the PlanElement.
        element_type {str} -- The category of the element. One of:
            'Plan Property', 'Structure', 'Reference Point'
        element_value {Value} -- The value of the PlanElement.
        unit {str} -- The units of the supplied value. (Only applies to
            numerical values).
    Attributes:
        name {str} -- The name of the PlanElement instance.
        element_type {str} -- The category of the element. One of:
            'Plan Property', 'Structure', 'Reference Point'
        element_value {Any} -- The numeric or text value of the property.
        unit {str} -- Defines the units of the PlanProperty value. Valid
            options depend on value_type.  Possible values are:
                ('%', 'Gy', 'cGy', 'cc', 'cm', 'N/A')
    Methods:
        define(element_value: Value, unit: str = None)->Tuple[Value, str]
            Set Element value.
            Returns:
                Tuple[Value, str] -- The Element value and corresponding units.
        get_value(self, constructor: str = '', **conversion_parameters)->Value
            Returns the requested value in the desired units.
        __repr__(self)->str
            Describe a Plan Element.
        __bool__(self)->bool
            Returns True if the element is not empty.
    '''
    def __init__(self, name: str = None, element_type: str = None,
                 element_value: Value = None, unit: str = None):
        '''Initialize the base properties of a PlanElement.
            If name is not supplied, return an object with self.name = None
            as the only attribute.
        Keyword Arguments:
            name {str} -- The name of the PlanElement.
            element_type {str} -- The category of the element. One of:
                'Plan Property', 'Structure', 'Reference Point'
            element_value {Value} -- The value of the PlanElement.
            unit {str} -- The units of the supplied value. (Only applies to
                numerical values).
        '''
        self.name = str(name)
        self.element_type = str(element_type)
        self.unit = None
        self.element_value = None
        self.define(element_value, unit)

    def define(self, element_value: Value = None,
               unit: str = None)->Tuple[Value, str]:
        '''Set Element value.
        Keyword Arguments:
            element_value {Value} -- The value of the PlanElement.
            unit {str} -- The units of the supplied value. (Only applies to
                numerical values).
        Returns:
            Tuple[Value, str] -- The Element value and corresponding units.
        '''
        try:
            self.element_value = float(element_value)
        except (ValueError, TypeError):
            self.element_value = element_value
        else:
            if unit:
                self.unit = str(unit)
            else:
                self.unit = None
        return (self.element_value, self.unit)

    def get_value(self, constructor: str = '',
                  **conversion: ConversionParameters)->Value:
        '''Returns the requested value in the desired units.
        Arguments:
            constructor {str} -- A string describing the method for generating
                the requested value from this plan element.
            conversion {ConversionParameters} -- A dictionary containing the
                data used to perform any necessary unit conversion.
        Returns:
            Value -- The requested value from the plan element.
        '''
        # Question Consider constructor as a regular expression to derive custom string values
        # e.g. site from Plan Name
        # Question can most of PlanElement become a generic Value type
        # Question can PlanElement become an abstract base class that has Structure, PlanValue and ReferencePoint as sub-types
        # Other plan items could then be added on for plan checking purposes as needed.
        if constructor:
            pass # not yet implemented
        initial_value = self.element_value
        initial_unit = self.unit
        if initial_value and initial_unit:
            final_value = convert_units(initial_value, initial_unit,
                                        **conversion)
        else:
            final_value = initial_value
        return final_value

    def __bool__(self)->bool:
        '''Indicate empty Element.
        Returns:
            bool -- True if the element is not empty.
        '''
        return bool(self.name)

    def __repr__(self)->str:
        '''Describe a Plan Element.
        Returns:
            str -- PlanElement Summary String.
        '''
        attr_str = 'name={}'.format(self.name)
        if self.unit:
            attr_str += ', unit={}'.format(self.unit)
        if self.element_value:
            attr_str += ', element_value={}'.format(self.element_value)
        return 'PlanElement(' + attr_str + ')\n'


class DVH():
    '''DVH dose data for a given structure.
    Arguments:
        columns {Header} -- Data on each column in the DVH table
        dvh_curve {DvhData} -- The DVH curve data.
    Attributes:
        dvh_columns {Header} -- Each element of the list is a dictionary
            corresponding to one column of data. The dictionary contains the
            following elements:
                'name': the name of the data column
                'unit': units defined for the column
        dvh_curve {np.array} -- An nxm array of Dose and Volume.
    Methods:
        select_columns(x_unit: str, y_type: str,
                       y_unit: str = None)->Tuple[int, int, str]
            Select the appropriate x and y DVH columns.
        get_dvh_point(self, x_column: int, y_column: int, x_value: float)->float
            Interpolate DVH curve to select a value.
        get_value(self, dvh_constructor: DvhConstructor,
                  **conversion_parameters)->PlanElement
            Return the value in the requested units.
    '''
    def __init__(self, columns: Header, dvh_curve: DvhData):
        '''Initialize a DVH data set.
        Arguments:
            columns {Header} -- Data on each column in the DVH table
            dvh_curve {DvhData} -- The DVH curve data.
        '''
        self.dvh_columns = columns
        self.dvh_curve = np.array(dvh_curve).T

    def select_columns(self, x_unit: str, y_type: str,
                       y_unit: str = None)->Tuple[int, int, str]:
        '''Select the appropriate x and y DVH columns.
        Arguments:
            x_unit {str} -- The required units for the x axis point.
            y_type {str} -- The type of value for the y axis.
                One of 'Dose' or 'Volume'.
            y_unit {str} -- The required units for the y axis point.
                (default: {None})
        Returns:
            Tuple[int, int, str] -- Index to x and y dvh columns, x_units for
                conversion if necessary.
        '''
        # Initially no columns have been identified and not x unit conversion
        x_column = y_column = x_possible = y_possible = None
        desired_x_unit = None
        for(index, column) in enumerate(self.dvh_columns):
            # Check to see if the column matches the "y" type
            if y_type in column['Data Type']:
                y_possible = index
                # The column can be used for "y"
                if y_unit and (y_unit in column['Unit']):
                    # If the "y" units match, use this column
                    y_column = index
            elif x_column is None:
                # If the column is not "y" type it must be "x" type
                x_possible = index
                if x_unit in column['Unit']:
                    # If the "x" units match, use this column
                    # Note that an x unit conversion won't be required.
                    x_column = index
                    desired_x_unit = None
                else:
                    # If the "x" units don't match, note that an x unit
                    # conversion may be required.
                    desired_x_unit = column['Unit']
        if x_column is None:
            # If no column with matching "x" units is found,
            # Use a column with the right type and do a unit conversion.
            x_column = x_possible
        if not y_column:
            # If no column with matching "y" units is found,
            # Use a column with the right type.
            y_column = y_possible
        return x_column, y_column, desired_x_unit

    def get_dvh_point(self, x_column: int, y_column: int, x_value: float)->float:
        '''Interpolate DVH curve to select a value.
        Arguments:
            x_column {int} -- Index to x dvh column.
            y_column {int} -- Index to y dvh column.
            x_value {float} -- x value to use in the interpolation.
        Returns:
            float -- The y value interpolated to the x point.
        '''
        data = self.dvh_curve
        # x_value must be within the range of the x data.
        if min(data[x_column]) < float(x_value) < max(data[x_column]):
            linear_interp = interp1d(data[x_column], data[y_column])
            target_value = float(linear_interp(x_value))
        else:
            # Question should I raise an error if the dvh interpolation fails?
            target_value = None
        return target_value

    def get_value(self, dvh_constructor: DvhConstructor,
                  **conversion_parameters)->PlanDataItem:
        '''Return the value in the requested units.
        Keyword Arguments:
            dvh_constructor {DvhConstructor} -- The parameters required to
                extract a point from the dvh curve. (default: {None})
            conversion_parameters: {ConversionParameters} -- A dictionary
                containing the data used to perform any necessary unit
                conversion.
        Returns:
            float -- the requested value from  the DVH curve.
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
        dvh_point = PlanDataItem(name=dvh_name,
                                element_value=dvh_value,
                                unit=dvh_unit)
        return dvh_point


class Structure():
    '''Plan data associated with a particular structure.
    Keyword Arguments:
        name {str} -- The name of the structure. (default: {None})
        properties {Dict[str, PlanElement]} -- The dose and volume
            properties. (default: {None})
        dvh {DVH} -- The DVH curve for the structure. (default: {None})
    Attributes:
        name {str} -- The name of the structure.
        element_type {str} -- The category of the element.
            Default is'Structure'.
        structure_properties {Dict[str, PlanElement]} -- The dose and volume
            properties of the structure.
        dose_data {DVH} -- The DVH data associated with the structure.
    Methods:
        add_element(properties: Dict[str, Value])->PlanElement
            Add or update a structure element.
        get_value(constructor: str = '',
                  conversion: ConversionParameters = None)->Value:
            Return the requested value in the desired units.
        __repr__(self)->str
            Describe a Plan Element.
        __bool__(self)->bool
            Returns True if the element is not empty.
    '''
    def __init__(self, name: str = None,
                 properties: Dict[str, PlanDataItem] = None,
                 dvh: DVH = None, element_type='Structure'):
        '''Initialize a structure.
        Keyword Arguments:
            name {str} -- The name of the structure. (default: {None})
            element_type {str} -- The category of the element.
                Default is'Structure'.
            properties {Dict[str, PlanElement]} -- The dose and volume
                properties. (default: {None})
            dvh {DVH} -- The DVH curve for the structure. (default: {None})
        '''
        self.name = str(name)
        self.element_type = str(element_type)
        self.structure_properties = properties
        self.dose_data = dvh

    def add_element(self, properties: Dict[str, Value])->PlanDataItem:
        '''Add or update a structure element.
        Arguments:
            properties {Dict[str, Value]} -- parameters defining an element:
                name {str} -- The name of the PlanElement instance.
                element_value {Value} -- The numeric or text value of the
                    property.
                unit {optional, str} -- If element_value is a number, the
                    units of that number.
        Returns:
            PlanElement -- The element added or updated
        '''
        element = PlanDataItem(**properties)
        self.structure_properties[element.name] = element
        return element

    def get_value(self, constructor: str = '',
                  **conversion: ConversionParameters)->Value:
        '''Return the requested value in the desired units.
        Keyword Arguments:
            constructor {str} -- The structure property or a DVH point
                description. (default: {''})
            conversion {ConversionParameters} -- A dictionary containing the
                data used to perform any necessary unit conversion.
                (default: {None})
        Returns:
            Value -- The requested value in the desired units.
        '''
        if not conversion:
            conversion = dict()
        volume_property = self.structure_properties.get('Volume')
        if volume_property:
            conversion['volume'] = volume_property.element_value
        else:
            # Question Do I want to raise an error if unit conversion tries to use an un-set volume?
            conversion['volume'] = 1.0
        dvh_constructor = parse_constructor(constructor)
        if dvh_constructor:
            element = self.dose_data.get_value(dvh_constructor)
        else:
            element = self.structure_properties.get(constructor)
        if element:
            value = element.get_value(**conversion)
        else:
            value = None
        return value

    def __bool__(self):
        '''Indicate empty Structure.
        Returns:
            bool -- True if the structure is not empty.
        '''
        return bool(self.name)

    def __repr__(self)->str:
        '''Describe a Structure.
        Returns:
            str -- A string summary of a structure.
        '''
        # Start with name of a structure
        text_items = dict(name=self.name)
        # Indicate the number of properties defined
        if self.structure_properties:
            properties_str = ' Contains {} properties'
            text_items['properties'] = properties_str.format(
                len(self.structure_properties))
        else:
            text_items['properties'] = ''
        # Indicate id DVH is defined
        if self.dose_data:
            text_items['dvh'] = ' Contains DVH'
        else:
            text_items['dvh'] = ''
        repr_string = '<Structure (name={name})\t{properties}\t{dvh}>\n'
        return repr_string.format(**text_items)


class DvhFile():
    '''Controls reading of a .dvh plan file.
    A subclass of io.TextIOBase with the following additional Attributes and
    Methods:
    Class Attributes:
        special_charaters {Dict[str, str]} -- A dict to convert special
            non-ASCII character strings to an equivalent ASCII string.
    Attributes:
        file_name {Path} -- The full path to a the dvh file.
        file {TextIOWrapper} -- the .dvh file as a text file stream object.
        do_previous {bool} -- Return the previous line at the next readline()
            call.
    Arguments:
        file_name {Path} -- The full path to the .dvh file.
        **kwds {dict} -- Arguments passed to the Path.open method.
    Methods:
        catch_special_char(raw_line: str)->str:
            Convert line to ASCII.
        readline(**kwds)
            read a line from the dvh file.
            **kwds are passed as parameters to the Path.open method.
        backstep():
            Set the next call to self.readline to return last_line.
        read_lines(break_cond: str = None)->str:
            Iterate through lines of text data until break_cond is encountered.
        read_data_elements(break_cond: str = None)->Dict[str, Value]:
            Iterate through lines of text data until break_cond is encountered,
            returning the parameters obtained from each line.
        load_dvh(self)->DVH
            Load a DVH table from a .dvh file.
        load_structure(self, name: str)->Structure
            Load data for a single structure from a .dvh file.
        load_structures(self)->Dict[str, Structure]
            Loads all structures in a dvh file.
        load_data(self)->Tuple[Dict[str, PlanElement], Dict[str, Structure]]
            Load data from the .dvh file.
    '''
    special_charaters = {'cm³': 'cc'}
    # TODO Move special_charaters to the config file

    def __init__(self, file_name: Path, **kwds):
        '''Open the file_name file to begin reading.
            Use utf_8 encoding by default.
        Arguments:
            file_name {Path} -- The full path to the .dvh file.
            **kwds are passed as parameters to the Path.open method.
        '''
        if not kwds.get('encoding'):
            kwds['encoding'] = 'utf_8'
        self.file = file_name.open(**kwds)
        self.file_name = file_name
        self._last_line = None
        self.do_previous = False

    def __del__(self):
        '''Close the file and then remove the instance.
        '''
        self.file.close()
        #super().__del__()

    def catch_special_char(self, raw_line: str)->str:
        '''Convert line to ASCII.
            Look for special character strings in the line and replace with
            standard ASCII. Remove all other non ASCII characters.
        Arguments:
            raw_line {str} -- The original string to be cleaned.
        Returns:
            str -- raw_line with all non-ASCII characters converted or removed.
        '''
        for (special_char, replacement) in self.special_charaters.items():
            if special_char in raw_line:
                patched_line = raw_line.replace(special_char, replacement)
            else:
                patched_line = raw_line
        bytes_line = patched_line.encode(encoding="ascii", errors="ignore")
        new_line = bytes_line.decode()
        return new_line

    def readline(self, **kwds)->str:
        '''Read in the next line of text file, remembering previous line.
            **kwds are passed as parameters to the Path.open method.
            if self.do_previous is True return the previous line.
        Returns:
            str -- A line of ASCII text from the .dvh file.
        '''
        if self.do_previous:
            new_line = self._last_line
            self.do_previous = False
        else:
            raw_line = self.file.readline(**kwds)
            new_line = self.catch_special_char(raw_line)
            self._last_line = new_line
        return new_line

    def backstep(self):
        '''Set the next call to self.readline to return last_line.
        '''
        self.do_previous = True

    def read_lines(self, break_cond: str = None)->str:
        '''Iterate through lines of text data until the stop iteration
        condition is met.
        break_cond defines the stop iteration condition.
        Arguments:
            break_cond {Optional[str]} -- A string to look for in the current
                text line to indicate the iteration should stop.
                If break_cond is None, iteration will stop at the beginning of
                the next blank line.
                If break_cond is a string, iteration will stop at the first
                occurrence of that string and the file pointer will be stepped
                back one line.
        Returns:
            str -- text_line: type str
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

    def read_elements(self, break_cond: str = None)->Dict[str, PlanDataItem]:
        '''Iterate through lines of text data and returning the resulting
        element parameters extracted from each line.
        Arguments:
            break_cond {Optional[str]} -- A string to look for in the current
                text line to indicate the iteration should stop.
                If break_cond is None, iteration will stop at the beginning of
                the next blank line.
                If break_cond is a string, iteration will stop at the first
                occurrence of that string and the file pointer will be stepped
                back one line. break_cond is passed through to read_lines.
        Returns:
            Dict[str, PlanElement] -- a dictionary of plan element extracted
                from the file. The keys are the names of the plan elements.
        '''
        def find_unit(text: str)->Tuple[str, str]:
            '''Return a unit string and name from a text.
            Arguments:
                text {str} -- Text containing an item name and it's units, surrounded
                    by []. e.g. "Volume [cm³]"
            Returns:
                Tuple[str, str] -- A two-string tuple with the item name and units.
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

        def parse_element(text_line: str)->PlanDataItem:
            '''convert a line of text into PlanElement parameters.
            Arguments:
                text_line {str} -- A line of text from the .dvh file.
            Returns:
                PlanElement -- The plan element extracted from the file.
            '''
            line_element = text_line.split(':', 1)
            (item_name, item_unit) = find_unit(line_element[0].strip())
            parameters = {'name': item_name,
                          'element_type': 'Plan Property',
                          'unit': item_unit,
                          'element_value': line_element[1].strip()}
            return PlanDataItem(**parameters)

        element_set = dict()
        for text_line in self.read_lines(break_cond):
            if ':' in text_line:
                element = parse_element(text_line)
                element_set[element.name] = element
        return element_set

    def load_dvh(self)->DVH:
        '''Load a DVH table from a .dvh file.
        Returns:
            DVH -- The DVH data obtained from the table.
        '''
        def parse_line(text: str)->List[float]:
            '''Split line into multiple numbers.
            Arguments:
                text {str} -- A row of dvh values.
            Returns:
                List[float] -- The text line converted into a lust of numbers.
            '''
            return [float(num) for num in text.split()]

        def make_column_list(dvh_header: str)->Header:
            '''Build a list of DVH column identifiers.
            Arguments:
                dvh_header {str} -- The text header line from the dvh file.
            Returns:
                Header -- A list of two item dictionaries with the following
                    entries:
                        'Data Type' {str} -- "Volume' or 'Dose',
                        'Unit' {str} -- The units ove values in the column.
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
        # pylint: disable=anomalous-backslash-in-string
        dvh_header_pattern = '''
                ([^\[]+) # everything until the first square bracket ([)
                [\[]     # ignore the opening square bracket ([)
                ([^\]]+) # everything inside the square brackets ([])
                [\]]     # ignore the closing square bracket (])
            '''
        re_dvh_header = re.compile(dvh_header_pattern, re.VERBOSE)
        dvh_header = re_dvh_header.findall(text_line)
        dvh_columns = make_column_list(dvh_header)
        dvh_list = [parse_line(text) for text in self.read_lines()]
        return DVH(columns=dvh_columns, dvh_curve=dvh_list)

    def load_structure(self, name: str)->Structure:
        '''Load data for a single structure from a .dvh file.
        Arguments:
            name {str} -- The structure name
        Returns:
            Structure -- The structure read in from a DVH file.
        '''
        structure_data = self.read_elements()
        self.readline()  # Skip blank line
        dvh_data = self.load_dvh()
        return Structure(name, structure_data, dvh=dvh_data)

    def load_structures(self)->Dict[str, Structure]:
        '''Loads all structures in a dvh file.
        Returns:
            Dict[str, Structure] -- A dictionary of structures with the
                structure name as key.
        '''
        text_line = self.readline()
        structure_set = dict()
        while text_line:
            if ':' in text_line:
                structure_name = text_line.split(':', 1)[1].strip()
                new_structure = self.load_structure(structure_name)
                structure_set[structure_name] = new_structure
            text_line = self.readline()
        return structure_set

    def load_data(self)->Tuple[Dict[str, PlanDataItem], Dict[str, Structure]]:
        '''Load data from the .dvh file.
        Returns:
            Tuple[Dict[str, PlanElement], Dict[str, Structure]] -- The plan
                elements and structures read in from the .dvh file.
        '''
        # Plan Parameters occur before structure data
        plan_parameters = self.read_elements(break_cond='Structure')
        plan_structures = self.load_structures()
        return (plan_parameters, plan_structures)

    def read_header(self)->Dict[str, PlanDataItem]:
        '''Read the header data for a .dvh file.
        Returns:
            Dict[str, PlanElement] -- The plan elements from the .dvh file.
        '''
        plan_info = self.read_elements(break_cond='Structure')
        return plan_info

PlanElements = Union[PlanDataItem, Structure]
# Possible elements to add to a Plan
PlanItemLookup = Dict[str, PlanElements]


DvhSource = Union[DvhFile, Path, str, None]
DvhReference = Union[DvhFile, List[Dict[str,Any]]]
# Optional methods for specifying the dvh data


def scan_for_dvh(plan_path: Path)->List[PlanDescription]:
    '''Load DVH file headers for all .dvh files in a directory.
    Arguments:
        plan_path {Path} -- A directory containing .dvh files.
    Returns:
        List[PlanDescription] -- A list containing descriptions of .dvh files.
    '''
    dvh_list = list()
    assert(plan_path.is_dir())
    for dvh_file in plan_path.glob('*.dvh'):
        dvh = DvhFile(dvh_file)
        try:
            header = dvh.read_header()
        except (EOFError, OSError, TypeError):
            continue # Ignore files that fail to read properly
        else:
            plan_info = PlanDescription(
                plan_file=dvh_file,
                file_type='DVH',
                patient_name = header['Patient Name'],
                patient_id = header['Patient ID'],
                plan_name = header['Plan'],
                course = header['Course'],
                dose = header['Prescribed dose'],
                export_date = header['Date']
                )
            dvh_list.append(plan_info)
        finally:
            del dvh  # Close the dvh file
            # Question keep the .dvh file open after scanning its header?
    return dvh_list


def get_dvh_list(config: ET.Element,
                 dvh_loc: DvhSource = None)->List[PlanDescription]:
    '''Load DVH file headers for all .dvh files in a directory.
    Arguments:
        config {ET.Element} -- An XML element containing default paths.
        dvh_loc {DvhSource} -- A DvhFile object, the path, to a .dvh file,
            the name of a .dvh file in the default DVH directory, or a
            directory containing .dvh files. If not given,
            the default DVH directory in config will be used.
    Returns:
        List[PlanDescription] -- A list containing descriptions of .dvh files.
    '''
    if isinstance(dvh_loc, DvhFile):
        dvh_data_source = dvh_loc
    elif isinstance(dvh_loc, Path):
        if dvh_loc.is_file():
            dvh_data_source = DvhFile(dvh_loc)
        elif dvh_loc.is_dir():
            dvh_data_source = scan_for_dvh(dvh_loc)
        else:
            return None
    elif isinstance(dvh_loc, str):
        dvh_dir = Path(config.findtext(r'./DefaultDirectories/DVH'))
        dvh_file_name = Path(config.findtext(r'./DefaultDirectories/DVH_File'))
        dvh_file = dvh_path / dvh_file_name
        dvh_data_source = DvhFile(dvh_file)
    else:
        dvh_dir = Path(config.findtext(r'./DefaultDirectories/DVH'))
        dvh_data_source = scan_for_dvh(dvh_dir)
    return dvh_data_source


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
        dvh_data_source:  type Path
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
def __init__(self, config: ET.Element, name: str = 'Plan',
                dvh_file: DvhSource = None):
    '''Load  the plan data.
    Arguments:
        config {ET.Element} -- An XML element containing default paths,
            settings and tables.
    Keyword Arguments:
        name {str} -- The name of the plan. Default is 'Plan'
        dvh_file {DvhSource} -- A DvhFile object, the path, to a .dvh file,
            or the name of a .dvh file in the default DVH directory. If not
            given, the default DVH file in config will be used.
            (default: {None})
    '''
    # TODO add ability to combine initial plan with new plan data
    # Need to make a plan to deal with data collisions
    self.name = str(name)
    # initialize class structure
    self.default_units = get_default_units(config)
    code_exceptions_def = config.find('LateralityCodeExceptions')
    laterality_exceptions = get_laterality_exceptions(code_exceptions_def)
    self.data_elements = {'Plan Property': dict(),
                            'Structure': dict(),
                            'Reference Point': dict()}

    # Set a .dvh file as the data source
    dvh_data = get_dvh(config, dvh_file)
    self.dvh_data_source = Path(dvh_data.file_name)

    # Load the dvh data
    (plan_parameters, plan_structures) = dvh_data.load_data()
    self.data_elements['Plan Property'].update(plan_parameters)
    self.data_elements['Structure'].update(plan_structures)

    # Derive laterality and dose
    self.laterality = self.get_laterality(laterality_exceptions)
    self.prescription_dose = self.set_prescription()

def add_data_item(self, element_category: str, element: PlanElements):
    '''Add a PlanElement as a new plan property.
    Arguments:
        element_category {str} -- The element type.  One of:
            'Plan Property'
            'Structure'
            'Reference Point'
        element {Elements} -- The element data to be added.
    '''
    element_entry = {element.name: element}
    self.data_elements[element_category].update(element_entry)
    LOGGER.debug('Created %s: %s', element_category, element.name)

def get_data_element(self, data_type: str, element_name: str)->PlanElements:
    '''Return the PlanElement of type property_type with property_name.
    Arguments:
        data_type {str} -- The element type.  One of:
            'Plan Property'
            'Structure'
            'Reference Point'The element data to be added.
        element_name {str} -- The name of the requested element.
    Returns:
        Elements -- The requested plan data item.
    '''
    data_group = self.data_elements.get(data_type)
    element = data_group.get(element_name) if data_group else None
    return element

def get_laterality(self, lat_exceptions: List[str])->Union[str, None]:
    '''Look for laterality indicator in plan name and use to set plan
        laterality.
    List[str] --

    Arguments:
        lat_exceptions {List[str]} -- A list of 4-letter body region codes
            which should not be treated as indicating laterality in the
            plan.
    Returns:
        Union[str, None] -- The plan laterality.  One of:
            'Right', 'Left', 'Both'
            or None if no laterality.
    '''
    # TODO need to deal with BOOS plan names
    lat_options = {'R': 'Right', 'L': 'Left', 'B': 'Both'}
    plan_name = self.get_data_element(
        data_type='Plan Property',
        element_name='Plan')
    body_region = plan_name.element_value[0:3]
    if body_region in lat_exceptions:
        return None
    lat_code = plan_name.element_value[3]
    return lat_options.get(lat_code, None)

def set_prescription(self)->PlanDataItem:
    '''Sets the prescription dose in the default units to enable unit
        conversion for other elements.
    Returns:
        PlanElement -- A 'prescription_dose' PlanElement in the plan
            default dose units.
    '''
    dose = self.get_data_element(data_type='Plan Property',
                                    element_name='Prescribed dose')
    dose_value = dose.element_value
    desired_units = self.default_units['DoseUnit']
    if dose.unit != desired_units:
        dose_value = convert_units(dose_value, dose.unit,
                                    desired_units)
    return PlanDataItem(name='prescription_dose',
                        element_value=dose_value,
                        unit=desired_units)

def items(self)->PlanItemLookup:
    '''provide a lookup dictionary of plan items.
    '''
    plan_items= dict()
    for group in self.data_elements.values():
        for name, element in group.items():
            plan_items[name] = element
    return plan_items

def types(self)->List[str]:
    '''Return a list of the different plan item types.
    '''
    return list(self.data_elements.keys())

def __repr__(self)->str:
    '''Describe a Plan.
    Returns:
        str -- Plan Summary String.
    '''
    attrs = dict(name=self.name, file_name=str(self.dvh_data_source))
    repr_string = '<Plan(Name={name}, DVH File = {file_name})>'
    repr_string += ' Contains:'
    repr_string = repr_string.format(**attrs)
    # Indicate the number of properties defined
    properties_str = ''
    template_str = '\n\t{count} of {type} elements.'
    for (data_type, element_set) in self.data_elements.items():
        if element_set:
            set_count = dict(type=data_type, count=len(element_set))
            properties_str += template_str.format(**set_count)
    repr_string += properties_str
    return repr_string

def load_plan(config, plan_path, name='Plan', type='DVH',
              starting_data: Plan = None)->Plan:
    '''Load plan data from the specified file or folder.
    '''
    if type in 'DVH':
        plan = Plan(config, name, DvhFile(plan_path))
    # starting_data currently ignored
    return plan

