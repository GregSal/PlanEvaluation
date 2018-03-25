'''Report on Plan parameters based on defined Criteria'''

from pathlib import Path
import xlwings as xw
from LoadData import load_items
from PlanData import Element


class ReportElement(Element):
    '''A base class for all ReportElement objects.
    A sub type of Element.
    Defines the source, category, and constructor.
    Attributes:
        source: type str
            The name of the PlanElement linked to this ReportElement
            If not specified, the Element name is used.
        cell_address:  type str
            The Excel cell address in "A1" format.
        cell_format:  type str
            The Excel number format to be used for the cell.  Examples:
                ('General', '@', '0.00', '0.00%', 'yyyy-mm-dd')
                If not specified, 'General' is used.
        category: type str
            Defines the subclass of the ReportElement.  Can be one of:
                ('Info', 'Property', 'Condition')
                If not specified, 'Info' is used.
    Methods
        __init__(self, cell_address, source=None, format='General',
                 category='Info', **element_parameters)
        define(self, source=None, format=None, category=None,
               **element_parameters)
        __repr__(self)
        add_to_report(self, sheet)
        Get properties
        Set status
        add_to_report
            Enter the value into the report and set the format.
        '''

    def __init__(self, cell_address, source=None, cell_format='General',
                 category='Info', **element_parameters):
        '''Initialize the attributes unique to Report Elements.
        '''
        super().__init__(**element_parameters)
        self.cell_address = str(cell_address)
        if source:
            self.source = source
        else:
            self.source = self.name
        self.cell_format = str(cell_format)
        self.category = str(category)

    def define(self, source=None, cell_format=None, category=None,
               **element_parameters):
        '''Define the Report Element.
        '''
        super().define(**element_parameters)
        if source:
            self.source = str(source)
        if cell_format:
            self.cell_format = str(cell_format)
        if category:
            self.category = str(category)

    def __repr__(self):
        '''Build an Element.
        '''
        repr_str = super().__repr__()
        repr_str = repr_str.replace('Element', 'ReportElement')
        attrs = ', cell_address={}, format={}, category={}'
        attr_str = attrs.format(self.cell_address, self.cell_format,
                                self.category)
        repr_str = repr_str[:-1] + attr_str + ')'
        return repr_str

    def add_to_report(self, sheet):
        '''enter the ReportElement into the spreadsheet.
        Parameters:
            sheet: type xlwings worksheet
                The worksheet to enter the value into.
        '''
        if self.cell_format:
            sheet.range(self.cell_address).number_format = self.cell_format
        if self.element_value:
            sheet.range(self.cell_address).value = self.element_value


class Report():
    '''Defines a Plan Evaluation Report.
    Attributes:
        template_file:  type Path
            The path to an Excel file used as a template for the report.
            If not given a blank file will be used
        save_file: type Path
            The name to use for saving the Excel Report file.
        worksheet: type str
            The name of the Excel worksheet to save the report in.
            If not given 'Plan Report' is used.
        report_elements:  type list of ReportElement
            A list of all report elements to be entered as part of the report.
    Methods
        __init__(self, name, template_file=None, save_file=None,
                 worksheet='Plan Report')
        define(self, element_list)
        get_properties(self, plan)
        build(self)
        '''

    def __init__(self, name, template_file=None, save_file=None,
                 worksheet='Plan Report'):
        '''Define the spreadsheet paths, worksheet name and Report Elements.
        '''
        self.name = str(name)
        # Template File
        self.template_file = str(template_file)
        self.worksheet = str(worksheet)
        if save_file:
            self.save_file = str(save_file)
        else:
            self.save_file = Path(r'.\Report.xls')
        self.report_elements = list()


    def define(self, element_list):
        '''Define all of the Report Elements.
        Parameters:
            element_list: list of dictionaries containing keys:
                'name', 'unit', 'cell_address', 'cell_format'
        '''
        for element in element_list:
            cell_address = element.pop('cell_address')
            self.report_elements.append(ReportElement(cell_address, **element))

    def get_properties(self, plan):
        '''Define all of the Report Elements.
        Parameters:
            plan: dictionary containing PlanElements.
            keys are PlanElement names.
            values are dictionaries defining element attributes
        '''
        for element in self.report_elements:
            if element.source in plan:
                element.define(**plan[element.source])

    def build(self):
        '''Open the spreadsheet and save the Report elements.
        '''
        if self.template_file:
            workbook = xw.Book(str(self.template_file))
        else:
            app1 = xw.App()
            workbook = app1.books[0]
        workbook.activate(steal_focus=False)
        sheetnames = [sheet.name for sheet in workbook.sheets]
        if self.worksheet in sheetnames:
            spreadsheet = workbook.sheets[self.worksheet]
        else:
            spreadsheet = workbook.sheets.add(self.worksheet)
        spreadsheet.activate()
        for element in self.report_elements:
            element.add_to_report(spreadsheet)
        workbook.save(str(self.save_file))


def main():
    '''Test
    '''
    template_file = \
        Path(r'..\Test Data\SABR  Plan Evaluation Worksheet Test Copy.xls')
    save_file = \
        Path(r'..\Test Data\SABR  Plan Evaluation Worksheet Test Save.xls')
    worksheet = 'EvalutionSheet 48Gy4F or 60Gy5F'
    report = Report('Test', template_file, save_file, worksheet)

    element_file = Path(r"..\Test Data\ReportReference.txt")
    elements_list = load_items(element_file)
    report.define(elements_list)

    plan_values_file = Path(r'..\Test Data\ElementValues.txt')
    element_values = load_items(plan_values_file)
    plan = {element['PlanElement']:
            dict([('element_value', element['element_value']), ])
            for element in element_values}

    report.get_properties(plan)
    report.build()


if __name__ == '__main__':
    main()
