
import re
import fitz
import numpy as np
import os
import openpyxl
import pandas as pd

def colors(integer):
    color_permutations = [
        (0.1, 0.5, 0.8),  # Blue shade
        (0.7, 0.2, 0.1),  # Red shade
        (0.2, 0.6, 0.3),  # Green shade
        (0.8, 0.7, 0.1),  # Yellow shade
        (0.5, 0.2, 0.7),  # Purple shade
        # Add more color permutations as needed
    ]
    
    selected_color = color_permutations[integer % len(color_permutations)]
    stroke_color = selected_color
    color_dict = {
        "stroke": stroke_color,
    }
    return color_dict


def highlight_PDF(paper, phrases, paper_highlight,q_num):
   # paper_highlight = paper_highlight
    if os.path.exists(paper_highlight):
        doc = fitz.open(paper_highlight)
        incremental = True
    else:
        doc = fitz.open(paper)
        incremental = False
    
    for page in doc:
        for phrase in phrases:            
            text_instances = page.search_for(phrase)

            for inst in text_instances:
                highlight = page.add_highlight_annot(inst)
                highlight.set_colors(colors(q_num))
                highlight.update()
    if incremental:
        doc.save(paper_highlight, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
    else:
        doc.save(paper_highlight)

def save_sheet(identity,df,out_path):
  # Define the file path
  file_name = out_path + '.xlsx'
  print("Saving to " + file_name)
  if not os.path.exists(file_name):
      workbook = openpyxl.Workbook()
      workbook.save(file_name)
      # Open the Excel file using Pandas ExcelWriter
      excel_writer = pd.ExcelWriter(file_name, engine='openpyxl')
      # Write the DataFrame to a new sheet
      sheet_name = identity + '-' + str(1)
      df.to_excel(excel_writer, sheet_name=sheet_name, index=False)
      # Save the changes to the Excel file
      excel_writer._save()
      print("\n" + f"Saving Outputs to Sheet {sheet_name}" + "\n")
  else:
      # If the file exists, open it using openpyxl and add the DataFrame to a new sheet
      workbook = openpyxl.load_workbook(filename=file_name)
      sheet_name = identity
      counter = 0
      while sheet_name in workbook.sheetnames:
          counter += 1
          sheet_name = identity + '-' + str(counter)
      print("\n" + f"Saving Outputs to Sheet {sheet_name}" + "\n")
      excel_writer = pd.ExcelWriter(file_name, engine='openpyxl', mode='a')
      df.to_excel(excel_writer, sheet_name=sheet_name, index=False)
      excel_writer._save()
      excel_writer.close()

