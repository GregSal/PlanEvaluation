'''
Created on Sun Mar 18 21:37:14 2018

@author: Greg
Defines Classes and Methods related to reading plan data and extracting
elements for analysis.
'''


from pathlib import Path
from functools import partial
import logging
import re
from scipy.interpolate import interp1d
import numpy as np


logging.basicConfig(level=logging.WARNING)
LOGGER = logging.getLogger(__name__)


def convert_units(starting_value, starting_units, target_units,
                  dose=1.0, volume=1.0):
    '''Take value in starting_units and convert to target_units.
    '''
    conversion_table = {'cGy': {'cGy': 1.0, '%': 1.0/dose, 'Gy': 0.01},
                        'Gy':  {'Gy': 1.0, '%': 100/dose, 'cGy': 100},
                        'cc':  {'cc': 1.0, '%': 1/volume},
                        '%':   {'%': 1.0,
                                'cGy': dose/100.0,
                                'Gy': dose/10000,
                                'cc': volume/100}
                       }
    conversion_factor = conversion_table[starting_units][target_units]
    new_value = float(starting_value)*conversion_factor
    return new_value


def add_laterality_indicator(structure_base_name: str, laterality,
                             plan_laterality=None):
    '''Add a letter to the end of a structure name to indicate the laterality
    of the structure.
    Possible letter suffixes are:
        Left            ' L'
        Right           ' R'
        Both            ' B'
        Contralateral   ' L' or ' R'
        Ipsilateral     ' R' or ' L'
    For Ipsilateral and Contralateral, the choice of left or right will
    depend on the plan laterality.
    '''
    laterality_adjustor = {
        'Left': {'Ipsilateral': ' L', 'Contralateral': ' R'},
        'Right': {'Ipsilateral': ' R', 'Contralateral': ' L'}
        }
    laterality_selector = {'Left': ' L', 'Right': ' R', 'Both': ' B'}
    if plan_laterality and laterality_adjustor.get(plan_laterality):
        # Add Ipsilateral and Contralateral terms to selector
        laterality_selector.update(laterality_adjustor[plan_laterality])
    structure_suffix = laterality_selector.get(laterality)
    if structure_suffix:
        updated_structure = structure_base_name + structure_suffix
    else:
        updated_structure = structure_base_name
    return updated_structure


class Element(object):
    '''base class for all plan PlanElement and ReportElement objects.
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
        convert_units(self, unit=None)
        get_value(self, unit=None, **source)
        __repr__(self)
        __bool__(self)
    '''
    def __init__(self, name=None, **parameter_values):
        '''Initialize the base properties of all PlanElements.
        If name is not supplied, return an object with self.name = None as the
        only attribute.
        '''
        if name:
            self.name = str(name)
            self.unit = None
            self.element_value = None
            self.define(**parameter_values)
        else:
            self.name = None

    def define(self, element_value=None, unit=None):
        '''Set Element Attributes.
        '''
        if element_value is not None:
            self.element_value = element_value
        if unit:
            self.unit = str(unit)

    def __bool__(self):
        '''Indicate empty Element.
        Return my truth value (True or False).
        '''
        return bool(self.name)

    def get_value(self,):
        '''Returns the requested value.
        '''
        return self.element_value

    def __repr__(self):
        '''Describe a Report Element.
        Add Report Element Attributes to the __repr__ definition of Element
        '''
        attr_str = 'name={}'.format(self.name)
        if self.unit:
            attr_str += ', unit={}'.format(self.unit)
        if self.element_value:
            attr_str += ', element_value={}'.format(self.element_value)
        return 'Element(' + attr_str + ')'


class PlanElement(Element):
    '''A single value item for the plan.  e.g.:
            ('Patient Name', 'Patient ID', 'Dose', 'Fractions', 'Plan Name',
            'Body Region', 'Laterality', 'Normalization')
    '''
    def __init__(self, element_value=None, **parameters):
        '''Initialize the base properties of all PlanElements.
        '''
        super().__init__(**parameters)
        if self.name:
            self.conversion_factors = dict()
            self.define(element_value)

    def define(self, element_value=None, **parameters):
        '''Set the value with the appropriate units.
        '''
        if parameters:
            super().define(**parameters)
        try:
            self.element_value = float(element_value)
        except (ValueError, TypeError):
            self.element_value = element_value

    def get_value(self, desired_unit=None, conversion_method=None,
                  **parameters):
        '''Returns the requested value in the desired units.
        '''
        initial_value = super().get_value(**parameters)
        if initial_value and desired_unit:
            final_value = conversion_method(initial_value, self.unit,
                                            desired_unit)
        else:
            final_value = initial_value
        return final_value

    def __repr__(self):
        '''Describe a PlanElement.
        Since no new attributes simple replace the Element name with
        PlanElement.
        '''
        repr_str = super().__repr__()
        repr_str = repr_str.replace('Element', 'PlanElement')
        return repr_str


class PlanReference(dict):
    '''Contains information used to reference an individual Plan value.
    Used to connect ReportElements and Plan data.
    The dictionary may contain the following items as applicable:
        reference_name:
            The expected name of the related PlanElement.
        reference_aliases:
            A list of alternative names for the related PlanElement.
        reference_type:
            The type of PlanElement.  Can be one of:
                ('Plan Property', Structure', 'Reference Point')
        reference_laterality:
            Indicates the laterality of a particular structure reference.
            Can be one of:
                ('Contralateral', 'Ipsilateral', 'Both', 'Left', 'Right')
        reference_constructor:
            A string describing the method for extracting the required value.
            Includes:
                ('Volume', 'Minimum', 'Maximum', 'Mean',
                'V' # ['%', 'Gy', cGy],
                'D' # ['%', 'cc'])
        Methods
            __init__(self, **parameters)
            define(self, reference_name=None, reference_type='Plan Property',
               **parameters)
            update(self, match)
'''
    def __init__(self, **parameters):
        '''Create the base dictionary and add values if supplied.
        '''
        super().__init__()
        if parameters:
            self.define(**parameters)

    def define(self, reference_type='Plan Property', reference_name=None,
               **parameters):
        '''Identify all reference related parameters and update the reference
        dictionary with them.
        Reference related parameters are expected to begin with 'reference_'.
        Returns parameters with the reference related items removed.
        '''
        self['reference_name'] = str(reference_name)
        self['reference_type'] = str(reference_type)
        if parameters:
            reference_keys = [key for key in parameters
                              if 'reference_' in key]
            for key in reference_keys:
                value = parameters.pop(key)
                self[key] = str(value)
        return parameters

    def update_match(self, match):
        '''Update reference information resulting from matching with
        plan_data.
        Remove Laterality.
        '''
        if match:
            (reference_type, reference_name) = match
            self['reference_name'] = reference_name
            self['reference_type'] = reference_type
            self.pop('reference_laterality', None)
        else:
            self['reference_name'] = None

    def add_aliases(self, list_of_aliases):
        '''Add a list of alternative reference names.
        '''
        self['reference_aliases'] = list_of_aliases

    def __repr__(self):
        '''Build an Target list string.
        '''
        repr_str = 'Element Reference: \n\t'
        parameter_str = ''.join('{}: {}\n\t'.format(name, value)
                                for (name, value) in self.items())
        repr_str += parameter_str
        return repr_str



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
    def __init__(self, columns=None, dvh_curve=None, conversion_method=None):
        '''Initialize a DVH data set.
        '''
        self.dvh_columns = columns
        self.dvh_curve = np.array(dvh_curve).T
        self.unit_conversion = conversion_method

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

    def get_value(self, dvh_constructor=None):
        '''Return the value in the requested units.
        '''
        (y_type, x_value, x_unit) = dvh_constructor
        (x_column, y_column, desired_x_unit) = \
            self.select_columns(x_unit, y_type)
        if desired_x_unit:
            x_value = self.unit_conversion(float(x_value),
                                           x_unit, desired_x_unit)
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
    def __init__(self, name=None, conversion_method=None, **properties):
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
            self.unit_conversion = conversion_method
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
        self.set_units()  # Update conversion_method with structure volume
        self.dose_data = DVH(columns=dvh_columns, dvh_curve=dvh_list,
                             conversion_method=self.unit_conversion)

    def get_value(self, reference_constructor='', **parameters):
        '''Return the value in the requested units.
        '''
        def parse_constructor(reference_constructor):
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
            dvh_constructor = re_construct.findall(reference_constructor)
            return dvh_constructor

        parameters['conversion_method'] = self.unit_conversion
        dvh_constructor = parse_constructor(reference_constructor)
        if dvh_constructor:
            element = self.dose_data.get_value(dvh_constructor[0])
        else:
            element = self.structure_properties.get(reference_constructor)
        if element:
            value = element.get_value(**parameters)
        else:
            value = None
        return value

    def set_units(self):
        '''Updates the unit conversion method to include the structure volume.
        '''
        volume_element = self.structure_properties.get('Volume')
        structure_volume = volume_element.element_value
        self.unit_conversion = partial(self.unit_conversion,
                                       volume=structure_volume)

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
    default_units = {'DoseUnit': 'cGy',
                     'VolumeUnit': '%',
                     'DistanceUnit': 'cm'
                    }

    def __init__(self, name, data_source):
        '''Define the path to the file containing the plan data.
        '''
        self.name = str(name)
        self.data_source = Path(data_source.file_name)
        self.data_elements = {'Plan Property': dict(),
                              'Structure': dict(),
                              'Reference Point': dict()}

        self.prescription_dose = PlanElement(name='prescription_dose')
        self.laterality = None
        self.unit_conversion = convert_units
        (plan_parameters, plan_structures) = data_source.load_data()
        self.add_plan_data(plan_parameters, plan_structures)


    def set_units(self, **default_units):
        '''Sets the default units for the plan data.
        Parameters
            One or more of the following:
                 DoseUnit: One of ('Gy', 'cGy', '%')
                 VolumeUnit: One of ('cc', '%')
                 DistanceUnit: 'cm')
        '''
        if default_units:
            for (unit_type, unit) in default_units.items():
                self.default_units[unit_type] = unit

    def add_data_item(self, element_category, element):
        '''Add a PlanElement as a new plan property.
        '''
        element_entry = {element.name: element}
        self.data_elements[element_category].update(element_entry)
        LOGGER.debug('Created %s: %s', element_category, element.name)

    def add_plan_property(self, parameters):
        '''Add a PlanElement as a new plan property.
        '''
        element = PlanElement(**parameters)
        self.add_data_item('Plan Property', element)

    def add_structure(self, name=None, **properties):
        '''Add a Structure to the plan.
        Build a unit conversion for the structure based on its volume.
        Parameters:
            name:  type str
                The name of the structure
            properties_list:  type list
                contains a list of dictionaries of structure properties
            dvh_columns
            dvh_list
        '''
        structure = Structure(name, conversion_method=self.unit_conversion,
                              **properties)
        self.add_data_item('Structure', structure)

    def add_plan_data(self, plan_parameters, structure_data_sets):
        '''Insert supplied plan parameters and structure data.
        Build a unit conversion for the plan based on the prescription dose.
        '''
        for parameters in plan_parameters:
            self.add_plan_property(parameters)
        self.set_prescription()
        self.set_laterality()
        for structure_data in structure_data_sets:
            self.add_structure(**structure_data)

    def get_data_group(self, data_type):
        '''Return a dictionary containing the plan properties of the
        requested type.
            data_type is one of:
                ('Plan Property', 'Structure', 'Reference Point')
        '''
        data_group = self.data_elements.get(data_type)
        return data_group

    def get_data_element(self, data_type, element_name):
        '''Return the PlanElement of type property_type with property_name.
        '''
        data_group = self.get_data_group(data_type)
        element = data_group.get(element_name) if data_group else None
        return element

    def match_element(self, reference_type=None, reference_name=None,
                      reference_laterality=None):
        '''Returns tuple of (reference_type, reference_name).
        '''
        full_reference_name = self.laterality_modifier(reference_name,
                                                       reference_laterality)
        match_pair = None
        if reference_type:
            plan_elements = self.get_data_group(reference_type)
        if plan_elements and reference_name:
            if full_reference_name in plan_elements:
                match_pair = (reference_type, full_reference_name)
        return match_pair

    def set_laterality(self):
        '''Look for laterality indicator in plan name and use to set
        laterality modifier.
        '''
        laterality_options = {'R': 'Right',
                              'L': 'Left',
                              'B': 'Both'}
        plan_name = self.get_data_element(
            data_type='Plan Property',
            element_name='Plan')
        laterality_code = plan_name.element_value[3]
        self.laterality = laterality_options.get(laterality_code)

    def laterality_modifier(self, name, laterality):
        '''Add suffix indicating laterality where appropriate.
        '''
        if laterality:
            full_name = \
                add_laterality_indicator(name, laterality,
                                         plan_laterality=self.laterality)
        else:
            full_name = name
        return full_name

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
        self.unit_conversion = partial(convert_units, dose=dose_value)
        self.prescription_dose = PlanElement(element_value=dose_value,
                                             unit=desired_units)

    def get_value(self, reference_type='', reference_name='', **parameters):
        '''Returns the requested value in the correct units.
        Calls get_value(parameters) method of PlanElement,
        Structure or ReferencePoint.
        '''
        plan_property = self.get_data_element(reference_type, reference_name)
        if plan_property:
            element_value = plan_property.get_value(
                conversion_method=self.unit_conversion,
                **parameters)
        else:
            element_value = None
        return element_value

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
