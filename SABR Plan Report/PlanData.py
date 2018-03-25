'''
Created on Sun Mar 18 21:37:14 2018

@author: Greg
Defines Classes and Methods related to reading plan data and extracting
elements for analysis.
'''


from pathlib import Path
import logging
import numpy as np


logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)


class Element(object):
    '''base class for all plan PlanElement and ReportElement objects.
    Defines the name, value_type, unit and value attributes.
    Attributes:
        name: type str
            The name of the PlanElement instance.
        value_type: type str
            Defines the type of value.  Can be one of:
                ('Text', 'Integer', 'Laterality', 'Dose, 'Ratio', 'Volume',
                'Distance')
        unit: type str
            Defines the units of the PlanProperty value. Valid options depend
            on value_type.  Possible values are:
                ('Percent', 'Gy', 'cGy', 'cc', 'cm', 'N/A')
        element_value:  type depends on value_type
            The numeric or text value of the property
    Methods
        __init__(self, name=None, **parameter_values)
        define(self, element_value=None, value_type=None,  unit=None, **not_used)
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
            self.value_type = None
            self.unit = None
            self.element_value = None
            self.define(**parameter_values)
        else:
            self.name = None

    def define(self, element_value=None, value_type=None, unit=None):
        '''Set Element Attributes.
        '''
        self.element_value = element_value
        self.value_type = str(value_type)
        self.unit = str(unit)

    def __bool__(self):
        '''Indicate empty Element.
        Return my truth value (True or False).'''
        return bool(self.name)

    def __repr__(self):
        '''Describe a Report Element.
        Add Report Element Attributes to the __repr__ definition of Element
        '''
        attr_str = 'name={}'.format(self.name)
        if self.value_type:
            attr_str += ', value_type={}'.format(self.value_type)
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

    def convert_units(self):
        '''Convert Units.
        '''
        pass

    def __repr__(self):
        '''Describe a PlanElement.
        Since no new attributes simple replace the Element name with
        PlanElement.
        '''
        repr_str = super().__repr__()
        repr_str = repr_str.replace('Element', 'ReportElement')
        return repr_str


class DVH():
    '''DVH dose data for a given structure.
    Attributes:
        columns:  type list of dictionaries
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
        self.columns = columns
        data = dvh_curve
        self.dvh_curve = np.array(data).T

    def get_dvh_value(self):
        '''Get a value'''
        pass

    def get_dvh_volume(self):
        '''Get a value'''
        pass

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
    def __init__(self, name=None, properties=None, dose_data=None):
        '''Initialize a structure.
        '''
        if name:
            self.name = str(name)
            self.properties = None
            self.dose_data = None
            self.define(properties, dose_data)
            LOGGER.debug('Created Structure %s', self.name)
        else:
            self.name = None

    def define(self, properties=None, dose_data=None):
        '''Set Element Attributes.
        '''
        if properties:
            self.properties = properties
        else:
            self.properties = dict()
        self.dose_data = dose_data

    def get_property(self):
        '''get a property.
        '''
        pass

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
        if self.properties:
            properties_str = \
                'Contains {} properties'.format(len(self.properties))
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
    Attributes:
        data_source:  type Path
            The path to a file containing the plan data.
        default_units:  type dict
             The default units for plan elements.
             Key-Value pairs are:
                 'DoseUnit': One of ('Gy', 'cGy', '%')
                 'VolumeUnit': One of ('cc', '%')
                 'DistanceUnit': 'cm')
        plan_properties type dict
            A dictionary of plan properties of a PlanElement sub-type.
        reference_points type dict
            A dictionary of plan elements of type ReferencePoint.
        structures type dict
            A dictionary of plan elements of type Structure.
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
    def __init__(self, name, data_source, **default_units):
        '''Define the path to the file containing the plan data.
        '''
        self.name = str(name)
        self.data_source = Path(data_source)
        self.default_units = dict(
            {'DoseUnit': 'cGy',
             'VolumeUnit': '%',
             'DistanceUnit': 'cm'
            })
        self.plan_properties = dict()
        self.reference_points = dict()
        self.structures = dict()
        if default_units:
            self.set_units(**default_units)

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

    def add_plan_property(self, parameters):
        '''Add a PlanElement as a new plan property.
        '''
        element = PlanElement(**parameters)
        self.plan_properties[element.name] = element

    def add_structure(self, name, properties_list=None,
                      dvh_columns=None, dvh_list=None):
        '''Add a Structure to the plan.
        Parameters:
            name:  type str
                The name of the structure
            properties_list:  type list
                contains a list of dictionaries of structure properties
            dvh_columns
            dvh_list
        '''
        dose_data = DVH(columns=dvh_columns, dvh_curve=dvh_list)
        structure_elements = dict()
        for element_properties in properties_list:
            element = PlanElement(**element_properties)
            structure_elements[element.name] = element
        structure = Structure(name, structure_elements, dose_data)
        self.structures[name] = structure

    def __repr__(self):
        '''Describe a Plan.
        '''
        # Start with name and path to plan
        attr_str = 'Plan name = {}\nPlan file = {}\n'.format(
            self.name, self.data_source)
        # Indicate the number of properties defined
        if self.plan_properties:
            properties_str = \
                'Contains {} properties\n'.format(len(self.plan_properties))
        else:
            properties_str = ''

        if self.reference_points:
            reference_points_str = 'Contains {} Reference Points\n'.format(
                len(self.reference_points))
        else:
            reference_points_str = ''

        if self.structures:
            structures_str = \
                'Contains {} structures\n'.format(len(self.structures))
        else:
            structures_str = ''

        repr_string = '< Type Plan(' + attr_str + ')' + properties_str +\
            reference_points_str + structures_str
        return repr_string
