'''A collection of GUI Helper classes
'''
#%% imports etc.
from abc import abstractproperty

from typing import Union, Dict, Tuple, List, NamedTuple, TypeVar, Generic

import PySimpleGUI as sg


from plan_report import ReferenceGroup


Values = Dict[str, List[str]]
ConversionParameters = Dict[str, Union[str, float, None]]


#%% GUI Appearance
sg.change_look_and_feel('LightGreen')
sg.SetOptions(element_padding=(0,0), margins=(0,0))


#%% Some helper classes because I am lazy
class ColumnSettings(NamedTuple):
    '''Settings for individual columns in a tree.
    Some of the settings that can be applied to an individual column.
    Positional Arguments:
        name {str} -- The column text.
        width {int} -- The default width of the column. Default is 30.
        show {bool} -- Display the column. Default is True.
    '''
    name : str
    width : int = 30
    show : bool = True


class ColumConfig(list):
    '''Column settings for a list of columns.
    A helper class that makes the defining and implementing of tree columns
    easier and clearer.
    '''
    def __init__(self, settings_list: List[ColumnSettings]):
        '''Generate a list of column settings.
        Arguments:
            settings_list {List[ColumnSettings]} -- A list of column settings
                for each column.  The list order should match the order of the
                items in the values passed to TreeData.  The list may contain
                one column with the name 'col0' - representing the key column.
                The settings for this column are removed from the name_list and
                width_list lists and separately assigned to column0 keyword
                arguments given by column_kwargs().
        '''
        super().__init__()
        for settings in settings_list:
            self.add(settings)

    def add(self, settings: ColumnSettings):
        '''Add settings for a column.
        '''
        # Reapply ColumnSettings conversion to allow for plain tuples
        # being passed.
        self.append(ColumnSettings(*settings))

    def name_list(self)->List[str]:
        '''Return a list of column names.
        '''
        return [col.name for col in self if 'col0' not in col.name]

    def width_list(self)->List[str]:
        '''Return a list of column widths.
        '''
        return [col.width for col in self if 'col0' not in col.name]

    def col0_width(self)->List[str]:
        '''Return the 0 column width.
        '''
        col0_settings = [col for col in self if 'col0' in col.name]
        if col0_settings:
            width = col0_settings[0].width
        else:
            width = None
        return width

    def show_list(self)->List[str]:
        '''Return a column display map.
        '''
        return [col.show for col in self if 'col0' not in col.name]

    def column_kwargs(self, **kwargs):
        '''returns a keyword dict of column settings for a tree.
        Creates the: headings, visible_column_map, col_widths and col0_width
        options.
        Appends any additional options provided.
        Arguments:
            Any valid Column keyword arguments.
        '''
        kwarg_dict = dict(
            headings=self.name_list(),
            visible_column_map=self.show_list(),
            col_widths=self.width_list())
        width0 = self.col0_width()
        if width0:
            kwarg_dict.update({'col0_width': width0})
        kwarg_dict.update(kwargs)
        return kwarg_dict


#%% Match  functions
class MenuDict(dict):
    '''Modifies a basic dictionary to defines a Default Menu if no matching
    selection is found.  Otherwise, just an ordinary dictionary.
    '''
    def __init__(self, *args, default=None, **kwargs):
        '''Accept a default definition at initialization.
        Arguments:
            default {List[Any}} -- The default menu. If not supplied use:
                ['Default', ['Default Menu', 'One', '&Two', '&More']
        '''
        super().__init__(self, *args, **kwargs)
        if default is None:
            default = ['Default', ['Default Menu', 'One', '&Two', '&More']]
        self.default_menu = default

    def __missing__(self, key):
        '''Return self.default_menu if key is not in the dictionary.
        '''
        return self.default_menu


class MenuChoices():
    '''Add options to modify the right-click menu.
    '''
    #@abstractproperty
    #def TKRightClickMenu(self):
    #    return None

    #@abstractproperty
    #def RightClickMenu(self):
    #    return None

    def set_menu(self, menu_dict: MenuDict = None):
        '''Add a menu selection dictionary to the element.
        Arguments:
            menu_choices {MenuDict, None} -- A dictionary with the values as
                Menu definition lists and the key, the reference to the menu.
        '''
        if menu_dict is None:
            self.menu_choices = MenuDict(default=self.RightClickMenu)
        else:
            self.menu_choices = menu_dict
        # Currently forces the default to be the menu definition passed to
        #     self.RightClickMenu.  Comment it out to allow a default defined
        #     in menu_dict
        #self.menu_choices.default_menu = self.RightClickMenu

    def clear_menu(self):
        '''Remove all menu items from a right-click menu.
        '''
        rt_menu = self.TKRightClickMenu
        # This call is directly to the Tkinter menu widget.
        rt_menu.delete(0,'end')

    def update_menu(self):
        '''Replace the current right-click menu with an updated menu contained
        in self.RightClickMenu.
        '''
        self.clear_menu()
        rt_menu = self.TKRightClickMenu
        menu =  self.RightClickMenu
        # This calls the sg menu creation method, normally called when the
        #     element is created.
        sg.AddMenuItem(rt_menu, menu[1], self)

    def select_menu(self, menu_key: str):
        '''Change the right-click menu based on the menu definition referenced
        by menu_key.
        Arguments:
            menu_key {str} -- The dictionary key for the desired menu. If
                menu_key does not match any item in the dictionary, the
                original menu definition given to self.RightClickMenu will be
                used.
        '''
        self.RightClickMenu = self.menu_choices[menu_key]
        self.update_menu()


class TreeRtClick(MenuChoices, sg.Tree):
    '''A variation of the sg.Tree class that replaces the right-click callback
    function with one that first selects the tree item at the location of the
    right-click and then modified the right-click menu accordingly.
    Arguments:
        menu_dict {MenuDict, None} -- A dictionary with Menu definition lists
            as the values and a string key as the reference to the menu.
        '''
    def get_key(self)->str:
        '''Get the appropriate menu key for the selected tree item.
        Returns:
            str -- The menu key for selecting the appropriate right-click menu
        '''
        selected_key = self.SelectedRows[0]
        ref = self.TreeData.tree_dict[selected_key].values
        if ref:
            return ref.reference_type
        # If ref is empty, then the right-click was not over an item.
        return None

    def update_value(self, new_value: ReferenceGroup):
        lookup = new_value.reference_index
        self.Update(key=lookup, value=new_value)

    def _RightClickMenuCallback(self, event):
        '''
        Replace the parent class' right-click callback function with one that
        first selects the tree item at the location of the right-click.
        Arguments:
            event {tk.Event} -- A TK event item related to the right-click.
        '''
        # Get the Tkinter Tree widget
        tree = self.Widget
        # These two calls are directly to the Tkinter Treeview widget.
        item_to_select = tree.identify_row(event.y) # Identify the tree item
        tree.selection_set(item_to_select)  # Set that item as selected.
        # Update the selected rows
        self.SelectedRows = [self.IdToKey[item_to_select]]
        # Set the corresponding menu.
        menu_key = self.get_key()
        if menu_key is None:
            # If menu_key is None, then the right-click was not over an item.
            # Ignore this rich-click
            return None
        # Set the appropriate right-click menu
        self.select_menu(menu_key)
        # Continue with normal right-click menu function.
        super()._RightClickMenuCallback(event)


#%% Live settings changer
class ConfigSetting(NamedTuple):
    element_name: str
    setting_name: str

Settings = TypeVar('Settings')
SettingsList = List[Tuple[str, Settings]]
StatusGroups = Dict[str, List[ConfigSetting]]


class ButtonSettings(NamedTuple):
    text: str = 'Select Report'
    button_color: Tuple[str, str] = ('red', 'white')
    disabled: bool = True


class ElementConfig(dict):
    def __init__(self, name: str, setting_type: Generic[Settings], 
                 settings: SettingsList, **dict_items):
        self.name = name
        self.setting_type = setting_type
        super().__init__(dict_items)
        self.load_settings(settings)

    def add_setting(self, setting_name, *setting: Settings):
        self[setting_name] = self.setting_type(*tuple(*setting))

    def load_settings(self, settings: SettingsList):
        for setting_group in settings:
            self.add_setting(*setting_group)

    def config(self, window: sg.Window, setting_name: str):
        desired_settings = self[setting_name]._asdict()
        window[self.name].update(**desired_settings)


class WindowConfig():
    def __init__(self, element_settings: List[ElementConfig],
                 status_groups: StatusGroups):
        super().__init__()
        self.element_lookup = dict()
        self.load_configs(element_settings)
        self.status_groups = dict(**status_groups)
        
    def add_config(self, setting: ElementConfig):
        self.element_lookup[setting.name] = setting

    def load_configs(self, element_settings: List[ElementConfig]):
        for setting in element_settings:
            self.add_config(setting)

    def config(self, window: sg.Window, setting: ConfigSetting):
        setting = ConfigSetting(*setting)
        element_config = self.element_lookup[setting.element_name]
        element_config.config(window, setting.setting_name)
        window.refresh()

    def set_status(self, window: sg.Window, status):
        for setting in self.status_groups.get(status, []):
            self.config(window, setting)
