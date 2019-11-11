
    patient_desc = [
        [sg.Text('Name:', size=(8,1)), sg.Text('', key='pt_name_text', size=(43,1))],
        [sg.Text('ID:', size=(8,1)), sg.Text('', key='id_text', size=(43,1))]
        ]
    patient_header = sg.Frame('Patient:', patient_desc,
                              key='patient_header',
                              size=(47,12),
                              title_location=sg.TITLE_LOCATION_TOP_LEFT,
                              font=('Calibri', 12),
                              element_justification='left')
    # Set Main Label
    plan_title = sg.Text(text='',
                         key='plan_title',
                         font=('Calibri', 14, 'bold'),
                         pad=((5, 0), (0, 10)),
                         size=(12,1),
                         justification='center')
    header_layout = [
        [plan_title],
        [sg.Text('Dose:', size=(8,1)), sg.Text('', key='dose_text', size=(40,1))],
        [sg.Text('Course:', size=(8,1)), sg.Text('', key='course_text', size=(40,1))],
        [sg.Text('Exported:', size=(8,1)), sg.Text('', key='exported_text', size=(40,1))],
        [patient_header]
        ]
    plan_header = sg.Frame('Plan', header_layout, key='plan_header',
                           font=('Arial Black', 14, 'bold'), size=(48,12),
                           element_justification='center',
                           title_location=sg.TITLE_LOCATION_TOP,
                           relief=sg.RELIEF_GROOVE, border_width=5,
                           visible=True)
    return plan_header

    column_settings = [
        ('File', False, 30),
        ('Type', False, 6),
        ('Patient Name', False, 12),
        ('Patient ID', False, 10),
        ('Plan Name', False, 6),
        ('Course', False, 5),
        ('Dose', True, 5),
        ('Fractions', False, 3),
        ('Exported On', True, 21)
        ]
    column_names = [col[0] for col in column_settings]
    show_column = [col[1] for col in column_settings]
    column_widths = [col[2] for col in column_settings]
    tree_settings = dict(key='Plan_tree',
                         headings=column_names,
                         visible_column_map=show_column,
                         col0_width=12,
                         col_widths=column_widths,
                         auto_size_columns=False,
                         justification='left',
                         num_rows=5,
                         font=('Verdana', 8, 'normal'),
                         show_expanded=True,
                         select_mode='browse',
                         enable_events=True)
    treedata = sg.TreeData()
    return sg.Tree(data=treedata, **tree_settings)
#%% Report Header
def create_report_header()->sg.Frame:
    template_layout = [
        [sg.Text('File:', size=(12,1)),
         sg.Text('', key='template_file', size=(25,1))],
        [sg.Text('WorkSheet:', size=(12,1)),
         sg.Text('', key='template_sheet', size=(25,1))],
        ]
    report_title = sg.Text(text='',
                           key='report_title',
                           font=('Calibri', 14, 'bold'),
                           size=(12,1),
                           pad=((5, 0), (0, 10)),
                           justification='center',
                           visible=True)
    report_desc = sg.Text(text='',
                          key='report_desc',
                          size=(30,1),
                          pad=(10, 3),
                          visible=True)
    template_header = sg.Frame('Template:', template_layout,
                                   key='template_header',
                                   title_location=sg.TITLE_LOCATION_TOP_LEFT,
                                   font=('Calibri', 12),
                                   element_justification='left')
    header_layout = [
        [report_title],
        [report_desc],
        [template_header]
        ]
    report_header = sg.Frame('Report', header_layout,
                             key='report_header',
                             title_location=sg.TITLE_LOCATION_TOP,
                             font=('Arial Black', 14, 'bold'), size=(30,20),
                             element_justification='center',
                             relief=sg.RELIEF_GROOVE, border_width=5)
    return report_header

def report_selector(report_definitions: Dict[str, Report]):
    '''Report Selection GUI
    '''
    #FIXME Add Blank as first item in selector
    report_list = [''] + [str(ky) for ky in report_definitions.keys()]
    report_selector_box = sg.Combo(report_list,
                                   key='report_selector',
                                   size=(40, 5),
                                   enable_events=True,
                                   readonly=True)
    return report_selector_box

sg.SetOptions(element_padding=(0,0), margins=(0,0))
load_plan_button = sg.Button(button_text='Load Plan', key='load_plan', disabled=False)
match_structures_button = sg.Button(button_text='Match Structures', key='match_structures', disabled=False)
generate_report_button = sg.Button(button_text='Show Report', key='generate_report', disabled=False)
layout = [[plan_header, report_header],
          [plan_selection, report_selection],
          [load_plan_button, match_structures_button, generate_report_button]
          ]

window = sg.Window('Plan Evaluation',
    layout=layout,
    resizable=True,
    debugger_enabled=True,
    finalize=True,
    element_justification="left")
def main_window(icons: IconPaths, plan_elements: PlanItemLookup,
                 reference_data: List[ReferenceGroup])->sg.Window:
    plan_header = create_plan_header(desc)
    report_header = create_report_header(report)
    w = sg.Window('Plan Evaluation',
        layout=[[plan_header, report_header]],
        default_element_size=(45, 1),
        default_button_element_size=(None, None),
        auto_size_text=None,
        auto_size_buttons=None,
        location=(None, None),
        size=(None, None),
        element_padding=None,
        margins=(None, None),
        button_color=None,
        font=None,
        progress_bar_color=(None, None),
        background_color=None,
        border_depth=None,
        auto_close=False,
        auto_close_duration=3,
        icon=None,
        force_toplevel=False,
        alpha_channel=1,
        return_keyboard_events=False,
        use_default_focus=True,
        text_justification=None,
        no_titlebar=False,
        grab_anywhere=False,
        keep_on_top=False,
        resizable=False,
        disable_close=False,
        disable_minimize=False,
        right_click_menu=None,
        transparent_color=None,
        debugger_enabled=False,
        finalize=True,
        element_justification="left")
    return window
    
    
def enter_value(reference_name):
    '''Simple pop-up window to enter a text value.
    '''
    title = 'Enter a value for {}.'.format(reference_name)
    layout = [[sg.InputText()], [sg.Ok(), sg.Cancel()]]
    window = sg.Window(title, layout, keep_on_top=True)
    event, values = window.Read()
    window.Close()
    if 'Ok' in event:
        return values[0]
    return None



#%% GUI settings
def match_window(icons: IconPaths, plan_elements: PlanItemLookup,
                 reference_data: List[ReferenceGroup])->sg.Window:
    # Constants
    column_names = ['Name', 'Type', 'Laterality', 'Match', 'Matched Item']
    show_column = [False, True, False, False, True]
    column_widths = [30,15,15,15,30]
    menu = plan_item_menu(plan_elements)
    tree_settings = dict(headings=column_names,
                         visible_column_map=show_column,
                         col0_width=30,
                         col_widths=column_widths,
                         auto_size_columns=False,
                         justification='left',
                         num_rows=20,
                         key='Match_tree',
                         show_expanded=True,
                         select_mode='browse',
                         enable_events=True,
                         right_click_menu=menu)
    # Tree data
    reference_set = make_reference_list(reference_data)
    # Plan Items for selecting
    treedata = sg.TreeData()
    treedata.Insert('','matched', 'Matched', [], icon=icons.path('match_icon'))
    treedata.Insert('','not_matched', 'Not Matched', [],
                    icon=icons.path('not_matched_icon'))
    for ref in reference_set:
        name = ref.match_name
        if ref.match_status:
            treedata.Insert('matched', name, name, ref)
        else:
            treedata.Insert('not_matched', name, name, ref)

    # Build window
    layout = [[sg.Text('Report Item Matching')],
              [sg.Tree(data=treedata, **tree_settings)],
              [sg.Button('Approve'), sg.Button('Cancel')]
             ]
    window = sg.Window('Match Items', layout=layout,
                       keep_on_top=True, resizable=True,
                       return_keyboard_events=False,  finalize=True)
    return window


