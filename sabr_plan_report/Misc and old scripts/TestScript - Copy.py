from pathlib import Path
from copy import deepcopy
import xml.etree.ElementTree as ET
import pandas as pd
import xlwings as xw
import re

from spreadsheet_tools import load_reference_table
from spreadsheet_tools import append_data_sheet, save_and_close

from build_sabr_plan_report import load_config, load_report_definitions
from plan_report import Report
from plan_data import DvhFile, Plan
from plan_data import get_laterality_exceptions


#%% Load Config File Data
test_path = Path.cwd() / 'Test Data'
config_file = 'PlanEvaluationConfig.xml'
config = load_config(test_path, config_file)

#%% Load Report Definitions
report_definitions = load_report_definitions(config)
report_name = 'SABR 48 in 4'
report = deepcopy(report_definitions[report_name])

#%% Load Plan File
dvh_file_name = 'test.dvh'
test_plan = Plan('Test Plan', config, dvh_file_name)

#%% Do match
(match, not_matched) = report.match_elements(test_plan)

report.get_values(test_plan)
# FIXME done to here
report.build()

#print(report)



#%%
#aliases_file = data_path / 'Aliases.xml'
#report_definition = data_path / 'ReportDefinitions.xml'
#alias_reference = load_aliases(aliases_file)
#report_tree = ET.parse(report_definition)
#report_root = report_tree.getroot()
#report_definitions = dict()
#for report_def in report_root.findall('Report'):
#    report = Report(report_def, alias_reference, data_path)
#    report_definitions[report.name] = report
##%% Save base structures
#sheet_info = {'base_path': Path.cwd(),
#              'file_name': 'Structure_base.xlsx',
#              'sheet_name': 'Structure base',
#              'starting_cell': 'A1',
#              'new_file': True,
#              'new_sheet': True,
#              'replace': True
#              }
#saved = append_data_sheet(all_root_structures, add_index=True, **sheet_info)
#save_and_close(saved)


##%% Load Laterality references
#laterality_lookup = load_laterality_table(config.find('LateralityTable'))
#default_patterns_def = config.find('DefaultLateralityPatterns')
#lat_patterns = load_default_laterality(default_patterns_def)
#plan_laterality = test_plan.laterality

##%% Add laterality
#report_item_name = 'LungV20'
#report_item = report.report_elements[report_item_name]

#reference = report_item.reference
#report_item_label = report.report_elements[report_item_name].label
#reference_type = reference['reference_type']
#plan_elements = test_plan.data_elements[reference_type]

## Try reference_name
#reference_name = reference['reference_name']
#matched_element = plan_elements.get(reference_name)
#if matched_element:
#    print('{}\t{}\t{}'.format(report_item_label, '', matched_element))

## add laterality
#item_laterality = reference.get('reference_laterality')
#if item_laterality:
#    for (pattern, size) in lat_patterns:
#        lat_index = (plan_laterality, item_laterality, size)
#        lat_indicator = laterality_lookup[lat_index]
#        lookup_name = pattern.format(Base=reference_name,
#                                     LatIndicator=lat_indicator)
#        matched_element = plan_elements.get(lookup_name)
#        if matched_element:
#            break
#if matched_element:
#    print('{}\t{}\t{}'.format(report_item_label, '', matched_element))

## Try Aliases
#aliases = reference.get('Aliases',{})
#for (pattern, size) in aliases:
#    if not size:
#        matched_element = plan_elements.get(pattern)
#    else:
#        lat_index = (plan_laterality, item_laterality, size)
#        print(lat_index)
#        lat_indicator = laterality_lookup[lat_index]
#        lookup_name = pattern.format(LatIndicator=lat_indicator)
#        matched_element = plan_elements.get(lookup_name)
#    if matched_element:
#        break
#print('{}\t{}\t{}'.format(report_item_label, '', matched_element))


#if not matched_element:
#    pass

#[('{Base} {LatIndicator}', 1)]

##%% Match Report and Plan Elements

#item_laterality = reference.get('Laterality')
#aliases = reference.get('Aliases',{})
#laterality_lookup = load_laterality_table(config.find('LateralityTable'))
#(match, not_matched) = report.match_elements(test_plan)
##%% simplest match
#reference = report.report_elements['HeartV28'].reference
#reference_name = reference['reference_name']
#reference_type = reference['reference_type']
#matched_element = test_plan.data_elements[reference_type][reference_name]

##%% plan property match
#reference = report.report_elements['PatientID'].reference
#item_laterality = reference.get('Laterality')
#reference_name = reference['reference_name']
#reference_type = reference['reference_type']
#matched_element = test_plan.data_elements[reference_type][reference_name]

##%% alias match
#report_item_name = 'ProxBronchMaxDose'
#reference = report.report_elements[report_item_name].reference
#reference_type = reference['reference_type']
#plan_elements = test_plan.data_elements[reference_type]
## Try reference_name
#reference_name = 'Bronchial Tree' # force alias
#matched_element = plan_elements.get(reference_name)
#print('{}\t{}\t{}'.format(report_item_name, '', matched_element))

## Try Aliases
#aliases = reference.get('Aliases',{})
#for (base, size) in aliases:
#    if not size:
#        matched_element = plan_elements.get(base)
#        if matched_element:
#            print('{}\t{}\t{}'.format(base, size, matched_element))
#            break


#item_laterality = reference['reference_laterality']

#default_pattern = '{Base} {LatIndicator}'
#default_size = 1

#match_item = dict()

#plan_laterality = test_plan.laterality
#reference = report.report_elements['LungV20'].reference
#item_laterality = reference['reference_laterality']
#match_item['Base'] = reference['reference_name']
#lookup_index = tuple([plan_laterality, item_laterality, default_symbol])
#lat_indicator = LateralityLookup['Indicator'][lookup_index]

#match_item['LatIndicator'] = lat_indicator
#match_text = default_pattern.format(**match_item)

#for element in report.report_elements:
#    reference = element.reference




    #def try_alias(match_method, reference, alias_list=None):
    #    '''Loop through aliases to find a match
    #    '''
    #    item_match = None
    #    if alias_list:
    #        for alias in alias_list:
    #            reference['reference_name'] = alias
    #            item_match = match_method(**reference)
    #            if item_match:
    #                break
    #    return item_match


#reference_sheet_info = {'file_name': 'Laterality.xlsx',
#                        'sheet_name': 'Laterality Patterns',
#                        'base_path': Path.cwd()}
#reference_table_info = {'starting_cell': 'A2', 'columns': 3}
#patterns = load_reference_table(reference_sheet_info, reference_table_info)
#patterns.set_index(['Location', 'Symbol'], inplace=True)

##%% Load Symbols Table
#reference_table_info = {'starting_cell': 'E2'}
#symbols = load_reference_table(reference_sheet_info, reference_table_info)
#symbols.set_index('Symbol', inplace=True)
