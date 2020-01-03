# -*- coding: utf-8 -*-
"""
Created on Mon Dec 30 13:50:52 2019

@author: gsalomon
"""

## ---(Mon Dec 30 13:13:50 2019)---
import zipfile
from pathlib import Path
import re
import xml.etree.ElementTree as ET

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


#document = zipfile.ZipFile('308970.doc')
#document = zipfile.ZipFile(r'L:/temp/QA Temp/308970.docx')
document = zipfile.ZipFile(r'L:/temp/QA Temp/Old/test.docx')
save_file = Path(r'L:/temp/QA Temp/CT SIM Worksheet.xml')
text_file = Path(r'L:/temp/QA Temp/CT SIM Worksheet.txt')
a = document.read(r'word/document.xml')
b = a.decode()
root = ET.fromstring(b)
c = ''
for row in root.findall(r'.//w:tbl//w:tc//w:p', namespaces=ns):
    r = ''
    for element in row.findall(r'.//w:t', namespaces=ns):
        r += f'{element.text}\t'
    for element in row.findall(r'.//w:ddList', namespaces=ns):
        lookup = [entry.attrib.get(f'{{{ns["w"]}}}val', None) 
                  for entry in element.findall(r'.//w:listEntry', namespaces=ns)]
        selected = element.find(r'.//w:result', namespaces=ns)
        if selected is None:
            selected_text = lookup[0]
        else:
            selected_text = lookup[int(selected.attrib.get(f'{{{ns["w"]}}}val'))]
        r += f'{selected_text}\t'
    d = r.strip()
    if d:
        e = re.sub(r'([^\t]*)\t[=: ]+', r'\1', d)
        c += f'{e}\n'
    
save_file.write_text(b)
text_file.write_text(c)

