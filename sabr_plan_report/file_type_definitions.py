'''
Created on Aug 26 2017

@author: Greg Salomons
GUI interface for DirScan.

Classes
    DirGui:
        Primary GUI window
        sub class of TKinter.Frame

'''
class FileTypes(list):
    '''A list of possible file types and their extensions.
    '''
    file_types = dict({'All Files':('*.*',),
                       'Text Files':('*.txt', '*.csv', '*.tab',
                                     '*.rtf', '*.text'),
                       'Excel Files':('*.xls', '*.xlsx', '*.xlsm'),
                       'Image Files':('*.jpg', '*.jpeg', '*.gif',
                                      '*.gif', '*.png',
                                      '*.tif', '*.tiff', '*.psd'),
                       'Comma Separated Variable File':('*.csv',),
                       'DVH File':('*.dvh',),
                       'Text File':('*.txt',),
                       'Excel 2003 File':('*.xls',),
                       'Excel 2010 File':('*.xlsx', '*.xlsm'),
                       'Word 2003 File':('*.doc',),
                       'Word 2010 File':('*.docx', '*.docm')})


    def __init__(self, type_selection=None):
        '''Create a user selectable list of file type options
        '''
        super().__init__()
        if type_selection is None:
            selection_list = list(self.file_types.keys())
        elif not isinstance(type_selection, list):
            raise TypeError('type_selection must be a list of strings')
        else:
            selection_list = type_selection
        for item in selection_list:
            try:
                self.append((item, ';'.join(self.file_types[item])))
            except KeyError:
                print(item + ' is not a valid file type set.')
