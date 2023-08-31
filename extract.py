
# ### Objective
# 
# In this notebook, we leverage LangChain framework to develop a dual-chatbot system to perform research paper digesting tasks. Our idea is to let one chatbot to play the role of "journalist", while letting the other chatbot play the role of "author". By watching the conversation between those two chatbots, the user can understand better the main message conveyed by the paper. Additionally, it is also possible for users to ask their own questions to guide the direction of the conversation.

# ### 1. Import necessary libraries

from embedding_engine import Embedder
from chatbot import force_format_ask, embed_paper, ask_question, format_bot
from auxiliary import save_sheet
#from pdfdocument.document import PDFDocument

from dotenv import load_dotenv
import os
import pandas as pd
import glob

load_dotenv()


proj_location = os.environ.get("PROJ_LOCATION")

# File folder with PDFs

pdf_location = proj_location + '/' + os.environ.get('PDF_LOCATION')
all_papers = glob.glob(pdf_location + "/*.pdf")
citations =[x.split('.pdf')[0] for x in [x.split('\\')[-1] for x in all_papers]]

topic = os.environ.get("TOPIC")

# Load Questions, Papers, and Prepare Data Output
question_parms = pd.read_csv(proj_location + '/ExtractionQuestions.csv', index_col=False)
all_questions = question_parms['Question'].tolist()
all_formats = question_parms['Response Format'].tolist()

# identities
identities = [s.strip() for s in os.environ.get("IDENTITIES").split(";")]


header = ['Citation'] + all_questions

# Initialize embedder
embedding = Embedder(engine = os.environ.get("EMBEDDING_ENGINE"))


all_data_df = pd.DataFrame()
paper_num = 0
# Iterate through papers
for paper in all_papers[:int(os.environ.get("DEBUG_N"))]:
    paper = paper.replace('\\', '/')
    print(paper)
    author = embed_paper(paper,embedding)
    q_num = 0

    all_responses = [citations[paper_num]]
    all_data = [citations[paper_num]]
    all_context = [citations[paper_num]]
    all_formatted_data = [citations[paper_num]]

    for question in all_questions:
        print("\n\n" + question + "\n\n")
        # Query Study
        response, data, context = force_format_ask(author,paper, question,q_num)
        print(data)
        format = all_formats[q_num]
        out = format_bot(data,topic,format)
        print("\n\n")
        print(out["formatted_data"])
        print("\n\n")
        all_formatted_data.append(out["formatted_data"])
        all_responses.append(response)
        all_data.append(data)
        all_context.append(context)
        # Format Data

        q_num += 1
    question_df = pd.DataFrame([all_formatted_data], columns=header)
    all_data_df = pd.concat([all_data_df,question_df],axis = 0, ignore_index=True)
    paper_num += 1

  # Save Results to excel

output_dir = proj_location + "/Output"

if not os.path.exists(output_dir):
    os.makedirs(output_dir)
identity = "none"
save_sheet(identity,all_data_df,output_dir)
