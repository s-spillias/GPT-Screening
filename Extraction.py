from dotenv import load_dotenv
import openai
import string
import fitz
import os
import shutil
import pandas as pd
import glob
import numpy as np
import torch
import random
import openpyxl
from sklearn.neighbors import NearestNeighbors
from transformers import AutoTokenizer, AutoModel
import re
import numpy as np
import openai
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter


load_dotenv()

#os.environ['TFHUB_CACHE_DIR'] = './model' # Where to save local embedding model.

proj_location = os.environ.get("PROJ_LOCATION")
debug = os.environ.get("DEBUG")
openAI_api_key = os.environ.get("OPENAI_API_KEY")
model_to_use = os.environ.get("EXTRACTION_MODEL_TO_USE")
temperature = int(os.environ.get("TEMPERATURE"))
n_agents = int(os.environ.get("N_AGENTS"))
n_retries = int(os.environ.get("N_RETRIES"))
rand_seed = os.environ.get("RAND_SEED")
code_out = os.environ.get("EXTRACTION_OUTPUT_FILE")
embedding_model = os.environ.get("EMBEDDING_MODEL")
topic = os.environ.get("TOPIC")
chunk_size = int(os.environ.get("CHUNK_SIZE"))



question_parms = pd.read_csv(proj_location + '/ExtractionQuestions.csv', index_col=False)

all_questions = question_parms['Question'].tolist()
prompt_type = question_parms['Response Format'].tolist()
text_source = question_parms['Text Source'].tolist()

exec(open('app.py').read())

# identities
identities = [s.strip() for s in os.environ.get("IDENTITIES").split(";")]

# File folder with PDFs
pdf_location = proj_location + '/' + os.environ.get('PDF_LOCATION')

all_files = glob.glob(pdf_location + "/*.pdf")

#remove_backmatter = True ## If True, this will ensure that the LLM doesn't see the Reference list.



# Dictionary of prompt types; numbers are the number of chunks sent to LLM
data_format = {'Quantitative': (3,'Return either a single value with any associated units. Or if multiple values are reported, return a list of all possible matching values found in the search results.'), 
               'Qualitative': (5,'Return a comprehensive response of up to three sentences.'), 
               'Categorical': (5,'Return a short phrase or single word only. Be as concise as possible. Do not explain or elaborate.'),
               'Theme': (4,'Return either a single item or a list where each element is at most three words. For each element, provide one or two examples from the study in a citation list after.'),
               'Multiple-Choice': (5,'Return only the applicable choices from the list provided in the Query without elaboration. Provide a quote from the study that justifies this choice in a citation after.')}

# Base Prompt for all queries. Screening Criteria information is included in 'Code/auxPDFs.py'
base_prompt = "Compose your answer strictly in two parts, 'Data' and 'Context', according to the format between **** below. Separate 'Data' and 'Context' using this symbol %% and ensure that the words 'Data' and 'Context' are present."\
              "\n****\n\nData: Answer to the query according to the Data Format.\n\n%%\n\n"\
              "Context: 'specific quotation from the study to support the Data above.\n\n"\
              "For each point in your Data, provide a specific quotation from the study for context."\
              "Only include information in the Data based on the study and don't include additional information. "\
              "Make sure the Data is correct and don't output false content. "\
              "In the Context section, return a numbered list of Quotations that correspond to the Data section,"\
              "and which provide context drawn from the study for the Data you have provided. Only include direct Quotations from the study."\
              "If the study does not relate to the Query, simply state 'No Relevant Data'."\
              
## Execute Coding

url = ''#"https://www.oecd.org/australia/34427707.pdf"

# ID all pdfs in target folder 

citations = [x.split('\\')[-1] for x in all_files]
citations = pd.DataFrame([x.split('.pdf')[0] for x in citations], index=None)
header = ['Citation'] + all_questions
    
    #"In the Data section, provide an answer to the query according to the Data Format."\
                # "'\n\nReflection - Reflect on whether the Initial Data accurately interprets the study with a brief justification.\n\n"\
              # "'\n\nFinal Data - Respond to the Reflection and provide a final answer to the query according to the Data Format.\n\n"\

for identity in identities:
  print('\nBeginnning Data Extraction \n\n')
  print('I am a ' + identity)

  all_data_df = pd.DataFrame([],index=None)
  all_context_df = pd.DataFrame([],index=None)
  for file in all_files:
    print("\n>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n")
    print(file)
    file_data = []
    file_context = []
    # Remove previous file
    for i in glob.glob(os.getcwd() + 'corpus*'):
        os.remove(i)
    # Add in new file
    shutil.copy2(file,'corpus.pdf')
    # Loop Through Questions
    for q_num in range(0,len(all_questions)):
        question = all_questions[q_num]
        type = text_source[q_num]
        #print(type)
        n_chunks = int(os.environ.get("N_CHUNKS"))
        print(">>>>>>>>")
        print(question)
        print(">>>>>>>>")
        ### Here is the Call to the LLM
        out = respond(question,type)
        # Append Responses
        file_data.append(out[0])
        #file_context.append(out[2])
    # Add responses as new row to dataframe.
    all_data_df = pd.concat([all_data_df,pd.DataFrame(file_data, index=None).T],axis = 0, ignore_index=True)
  #  all_context_df = pd.concat([all_context_df,pd.DataFrame(file_context, index=None).T],axis = 0, ignore_index=True)



  all_data = pd.concat([citations,all_data_df],axis = 1, ignore_index=True)
 # all_context = pd.concat([citations,all_context_df],axis = 1, ignore_index=True)

  all_data.columns = header
  #all_context.columns = header

  # Save Results to excel

  output_dir = proj_location + "/Output"

  if not os.path.exists(output_dir):
      os.makedirs(output_dir)

  save_sheet(identity,all_data)

