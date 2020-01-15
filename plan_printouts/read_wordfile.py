# -*- coding: utf-8 -*-
"""
Created on Mon Dec 30 13:50:52 2019

@author: gsalomon
"""

## ---(Mon Dec 30 13:13:50 2019)---
import zipfile
from datetime import datetime, timedelta
from file_utilities import set_base_dir
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import win32com.client

#%%
#document_folder = Path(r'\\VARIMGPV1\va_data$\Filedata\Documents\Files')
#no_dif = timedelta(0)
#expected_date = datetime.strptime(r'12/13/2019  1:38:03 PM',r'%m/%d/%Y %I:%M:%S %p')
#for file in document_folder.glob('*.doc'):
#    file_date = datetime.fromtimestamp(int(file.stat().st_mtime))
#    if file_date-expected_date == no_dif:
#        print(file.name)

#%%
#document_folder = Path(r'\\VARIMGPV1\va_data$\Filedata\Documents\Files')
#save_folder = Path(r'L:\temp\Plan Checking Temp')
#file_name = '311566.doc'
#doc_file = document_folder / file_name
#docx_file = save_folder / file_name.replace('doc', 'docx')
#word = win32com.client.Dispatch("Word.application")
#try:
#    wordDoc = word.Documents.Open(str(doc_file))
#    wordDoc.SaveAs2(str(docx_file), FileFormat = 16)
#    wordDoc.Close()
#except Exception as e:
#    print('Failed to Convert: {0}'.format(doc_file))
#    print(e)
#%%
    
ns = {'wpc': r"http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas",
      'mc': r"http://schemas.openxmlformats.org/markup-compatibility/2006",
      'o': r"urn:schemas-microsoft-com:office:office",
      'r': r"http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      'm': r"http://schemas.openxmlformats.org/officeDocument/2006/math",
      'v': r"urn:schemas-microsoft-com:vml",
      'wp14': r"http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing",
      'wp': r"http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
      'w10': r"urn:schemas-microsoft-com:office:word",
      'w': r"http://schemas.openxmlformats.org/wordprocessingml/2006/main",
      'w14': r"http://schemas.microsoft.com/office/word/2010/wordml",
      'wpg': r"http://schemas.microsoft.com/office/word/2010/wordprocessingGroup",
      'wpi': r"http://schemas.microsoft.com/office/word/2010/wordprocessingInk",
      'wne': r"http://schemas.microsoft.com/office/word/2006/wordml",
      'wps': r"http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
      }

#%%
#document = zipfile.ZipFile('308970.doc')
#document = zipfile.ZipFile(r'L:/temp/QA Temp/308970.docx')
document = zipfile.ZipFile(docx_file)
save_file = save_folder / 'CT SIM Worksheet.xml'
text_file = save_folder / 'CT SIM Worksheet.txt'
a = document.read(r'word/document.xml')
b = a.decode()
root = ET.fromstring(b)
c = ''
for para in root.findall(r'.//w:p', namespaces=ns):
    for element in para.iter():
        txt = element.text
        if txt is None:
            continue
        elif 'FORMDROPDOWN' in txt:
            for ddlist in para.findall(r'.//w:ddList', namespaces=ns):
                lookup = [entry.attrib.get(f'{{{ns["w"]}}}val', None) 
                          for entry in ddlist.findall(r'.//w:listEntry', namespaces=ns)]
                selected = ddlist.find(r'.//w:result', namespaces=ns)
                if selected is None:
                    selected_text = lookup[0]
                else:
                    selected_text = lookup[int(selected.attrib.get(f'{{{ns["w"]}}}val'))]
                c += f'{selected_text}\t'
        elif 'FORMCHECKBOX' in txt:
            checkb = para.find(r'.//w:checkBox', namespaces=ns)
            selected = checkb.find(r'.//w:checked', namespaces=ns)
            if selected is None:
                c += 'No\t'
            else:
                c += 'Yes\t'
        elif 'FORMTEXT' not in txt:
            c += f'{txt}\t'
    c += '\r\n'
# remove blank lines
    out_text = ''
for line in c.splitlines():
    if line:
        out_text += line + '\n'
text_file.write_text(out_text, errors='replace')
