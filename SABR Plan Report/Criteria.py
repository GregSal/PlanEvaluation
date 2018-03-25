'''Defines classes and methods used to construct a plan evaluation criteria.
'''

class Element(object):
    '''base class for all plan PlanElement and ReportElement objects.
    Defines the name, value_type, unit and value attributes.
	Attributes:
		name: type str
            The name of the PlanElement instance.
        value_type: type str
			Defines the type of value.  Can be one of:
                ('Text', 'Integer', 'Laterality', 'Dose, 'Ratio', 'Volume', 'Distance')
		unit: type str
            Defines the units of the PlanProperty value. Valid options depend on
            value_type.  Possible values are:
			    ('Percent', 'Gy', 'cGy', 'cc', 'cm', 'N/A')
        value:  type depends on value_type
            The numeric or text value of the property
    Methods
		__init__(self, name, source, **kwds):
    '''
    def __init__(self, name, source, **kwds):
        '''Initialize the base properties of all PlanElements.
        '''
        self.name = str(name)
        self.source = source
        if kwds.get('value_type'):
            self.value_type = str(value_type)
        if kwds.get('unit'):
            self.unit = str(unit)
        if kwds.get('value'):
            self.value = value

    def define(**kwds):
        '''Define the Element.
        '''
        pass


class ReportElement(PlanElement):
    '''A base class for all ReportElement objects.
    A sub type of Element.

    Defines the source, category, and constructor.
	Attributes:
		name: type str
            The name of the PlanElement instance.
        category: type str
			Defines the subclass of the PlanElement.  Can be one of:
                ('Text', 'Ratio', 'Dose'. 'Volume', 'Distance')
		unit: type str
            Defines the units of the PlanElement value. Valid values depend on
            the subclass.  Possible values may include:
			    ('Percent', 'Gy', 'cc', 'cm', 'N/A')
        source: type tuple of str
            The name of a plan element or a pair of properties from which this
            PlanElement is derived.
        constructor: type str
            A string that defines the method used for extracting the PlanElement
            from the plan.  For more information on this see the individual
            PlanElement subclasses.
        value:  type depends on category
            The numeric or text value of the property
    Methods
		define(name, source, **kwds)
    '''
    def __init__(self, name, source, **kwds):
        '''Initialize the base properties of all PlanElements.
        '''
        self.name = str(name)
        self.source = source
        if kwds.get('category'):
            self.category = str(category)
        if kwds.get('unit'):
            self.unit = str(unit)
        if kwds.get('constructor'):
            self.constructor = str(constructor)
        if kwds.get('value'):
            self.value = value





class TextElement(str, PlanElement):
    '''A subclass of PlanElement with a value of type str.
    '''
    def __init__(self, unit, source, constructor, **kwds):
        self.category = 'Text'
        self.unit = 'N/A'
        self.constructor = ''
        super().__init__(**kwds)


class NumElement(float, PlanElement):
    '''A subclass of PlanElement with a value of type float.
    '''
    def __init__(self, **kwds):
        super().__init__(**kwds)


class DoseElement(NumElement):
    '''A subclass of NumElement containing a Dose value.
    '''
    pass


class VolumeElement(NumElement):
    '''A subclass of NumElement containing a Volume value.
    '''
    pass


class DistanceElement(NumElement):
    '''A subclass of NumElement containing a Distance value.
    '''
    pass


class RatioElement(NumElement):
    '''A subclass of NumElement defined as a Ratio of two other Properties.
    '''
    pass



class PlanElement(object):
    '''A base class for all plan PlanElement objects.
    Defines the source, category, unit and constructor.
	Attributes:
		name: type str
            The name of the PlanElement instance.
        category: type str
			Defines the subclass of the PlanElement.  Can be one of:
                ('Text', 'Ratio', 'Dose'. 'Volume', 'Distance')
		unit: type str
            Defines the units of the PlanElement value. Valid values depend on
            the subclass.  Possible values may include:
			    ('Percent', 'Gy', 'cc', 'cm', 'N/A')
        source: type tuple of str
            The name of a plan element or a pair of properties from which this
            PlanElement is derived.
        constructor: type str
            A string that defines the method used for extracting the PlanElement
            from the plan.  For more information on this see the individual
            PlanElement subclasses.
        value:  type depends on category
            The numeric or text value of the property
    Methods
		define(name, source, **kwds)
    '''
    def __init__(self, name, source, **kwds):
        '''Initialize the base properties of all PlanElements.
        '''
        self.name = str(name)
        self.source = source
        if kwds.get('category'):
            self.category = str(category)
        if kwds.get('unit'):
            self.unit = str(unit)
        if kwds.get('constructor'):
            self.constructor = str(constructor)
        if kwds.get('value'):
            self.value = value


    def define()


class TextElement(str, PlanElement):
    '''A subclass of PlanElement with a value of type str.
    '''
    def __init__(self, unit, source, constructor, **kwds):
        self.category = 'Text'
        self.unit = 'N/A'
        self.constructor = ''
        super().__init__(**kwds)


class NumElement(float, PlanElement):
    '''A subclass of PlanElement with a value of type float.
    '''
    def __init__(self, **kwds):
        super().__init__(**kwds)


class DoseElement(NumElement):
    '''A subclass of NumElement containing a Dose value.
    '''
    pass


class VolumeElement(NumElement):
    '''A subclass of NumElement containing a Volume value.
    '''
    pass


class DistanceElement(NumElement):
    '''A subclass of NumElement containing a Distance value.
    '''
    pass


class RatioElement(NumElement):
    '''A subclass of NumElement defined as a Ratio of two other Properties.
    '''
    pass


class Status(str):
    '''Defines the status of a condition.
    Can be one of:
        ('Fail', 'Warn', 'Goal', 'Info')
			Fail:  Major Deviation
			Warn:  Minor Deviation
			Goal:  Strive For
			Info:  Record
    '''
    pass


class Condition(object):
    ''' A PlanElement test used for plan evaluation.

	Methods
		define(test_property, test_method, if_true, if_false)
            Defines the PlanElement, test method and possible return values
		evaluate
    	construct
            Obtains PlanElement value, applies test method and returns true or false argument
            if argument to be returned is another Condition, it applies the construct method to that Condition.
			Builds value from passed sources and methods
		'''
    pass


def define_PlanElement():
	'''returns appropriate PlanElement subclass.
            link: type PlanLink
            Contains the status of the link between the PlanElement and a plan.
'''
