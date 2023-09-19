
# ### Objective
# 
# In this notebook, we leverage LangChain framework to develop a dual-chatbot system to perform research paper digesting tasks. Our idea is to let one chatbot to play the role of "journalist", while letting the other chatbot play the role of "author". By watching the conversation between those two chatbots, the user can understand better the main message conveyed by the paper. Additionally, it is also possible for users to ask their own questions to guide the direction of the conversation.

# ### 1. Import necessary libraries

from embedding_engine import Embedder
from chatbot import embed_paper, ask_question, format_bot
from auxiliary import save_row,match_title,generate_text,get_abstract
#from pdfdocument.document import PDFDocument

from dotenv import load_dotenv
import os
import pandas as pd
import glob
from unidecode import unidecode
import re
from KG_chain import KG_chain, KG_save, extract_unique_values


load_dotenv()


proj_location = os.environ.get("PROJ_LOCATION")

# File folder with PDFs
screen_file = proj_location + '/Output/Screen.xlsx'  # Replace with the path to your Excel file

pdf_location = proj_location + '/' + os.environ.get('PDF_LOCATION')
all_papers = glob.glob(pdf_location + "/*.pdf")
default_model = os.environ.get("EXTRACTION_MODEL_TO_USE")


# Clean paper names; remove quotations, UTF characters, and trailing spaces.
for paper in all_papers:
    os.rename(paper, unidecode((re.sub('[“”"]', '',paper)).replace(' .pdf','.pdf')))

# Compile list of paper names
citations =[x.split('.pdf')[0] for x in [x.split('\\')[-1] for x in all_papers]]

# Load Questions, Papers, and Prepare Data Output
topic = os.environ.get("TOPIC")

question_parms = pd.read_csv(proj_location + '/ExtractionQuestions.csv', index_col=False)
all_questions = question_parms['Question'].tolist()
all_formats = question_parms['Response Format'].tolist()

# identities
identities = [s.strip() for s in os.environ.get("IDENTITIES").split(";")]


header = ['Citation'] + all_questions

# Initialize embedder
embedding = Embedder(engine = os.environ.get("EMBEDDING_ENGINE"))

output_dir = proj_location + "/Output"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

all_data_df = pd.DataFrame()

# Iterate through papers
for identity in identities:
    print(f"My identity is: {identity}")
    
    save_row(identity,header,output_dir)
    for paper_num in range(int(os.environ.get("RESTART_INDEX")),len(all_papers)):
        print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
        # End interation early according to variables in '.env'
        try:
            max_paper = int(os.environ.get("N_PAPERS"))
            if paper_num >= int(os.environ.get("N_PAPERS")):
                break
        except:
            print("Extracting All")

        # Set current paper
        paper = all_papers[paper_num].replace('\\', '/')
        print(paper)
        
        KG_csv = paper.replace('pdfs',"KG").replace('.pdf','.csv')
        memory = []
        entities = set()

        # Remove any pdfs that are not accepted by the Screen Document. 'Yes' in the summary sheet 'Accept' column.
        if not match_title(screen_file,paper):
            irrelevant_paper = True
            print("####\n\nSkipping Rejected pdf\n\n####")
            save_row('kicked',[paper],proj_location + '/kicked')
            paper_num += 1
            continue
        
        else:
            
            metadata = pd.read_excel(screen_file, sheet_name=os.environ.get("SCREEN_NAME") + "_summary")
            title = paper.split(' - ')[-1].replace('.pdf','')
            abstract = get_abstract(title,metadata)
        # Create embeddings; OCR is attempted if the paper is not machine-readable. If this fails, look for eccentricities in the file names (i.e. special characters, etc.)
        try:
            vectorstore = embed_paper(paper,embedding)
            unreadable_pdf = False
        except:
            unreadable_pdf = True

        # Screen

        if os.environ.get("EXTRACTION_SCREEN") == True:
            screen = f"Does this paper provide a specific example of f{topic}?"

            decision, context = ask_question(paper,screen,0,vectorstore,identity,memory,'mmr',default_model,'')

            if "NO" in (decision.upper())[:5] or "NO DATA" in decision.upper():
                irrelevant_paper = True
            else:
                irrelevant_paper = False
        else:
            irrelevant_paper = False


        case_question = f"Using the following context, complete this sentence: 'The example of {topic} described here is______'. Tip: return the full sentence. Context: {abstract}."
        case_study = generate_text(os.environ.get("OPENAI_API_KEY"), case_question, 1, 'gpt-4-0613').choices[0].message['content']
        # num_cases, context = ask_question(paper,case_question,0,vectorstore,identity,memory,'mmr',model_name='gpt-4-0613')
        
        print('\n\n' + case_study + '\n\n')
        graph = KG_chain(case_study,KG_csv,entities)
        memory.append(graph['tuples1'])
        
        # Save entities
        new_entities = extract_unique_values(graph['tuples1'])
        for item in new_entities:
            entities.add(item)
        # Initialize question counter
        q_num = 0

  
        # Initialize lists to receive data
        all_responses = [citations[paper_num]]
        all_data = [citations[paper_num]]
        all_context = [citations[paper_num]]
        all_formatted_data = [citations[paper_num]]
        
        # Iterate through each question in '/ExtractionQuestions.csv'
        for question in all_questions:
            # End interation early according to variables in '.env'
            try:
                max_question = int(os.environ.get("N_QUESTIONS"))
                if q_num >= int(os.environ.get("N_QUESTIONS")):
                    break
            except:
                print("Extracting All Questions")

            print("\n\n" + question + "\n\n")

            # Initialize lists for each question to accommodate multiple AI agents. Set number in .env 'N_AGENTS'
            responses = []
            datum = []
            contexts = []


            # Query the LLM multiple times
            for agent in range(int(os.environ.get("N_AGENTS"))):
                print(f"Agent {agent + 1}")
                            # If the paper is unreadable, this try block allows the code to continue so that placeholder data can be recorded below.
               # print(relevant_docs)
                # Write place-holder data if pdf is 'unreadable' or 'irrelevant'
                if unreadable_pdf:
                    data,context = 2*['UNREADABLE PDF']
                elif irrelevant_paper:
                    data,context = 2*['IRRELEVANT PAPER']
                # Otherwise query LLM with context from the vectorstore and the relevant question.
                else:
                    data, context = ask_question(paper, question,q_num,vectorstore,identity,memory,"mmr",default_model,case_study)
             #  print(context)
                # Append results to lists
                datum.append(data)
                contexts.append(context)
                
                

            # Gather all agent responses to be summarised in the desired format. 
            # Formats are specified in '/ExtractionQuestions.csv'
            # They are defined in 'chatbot.format_bot'
            format = all_formats[q_num]
            print("\n\n")
            print("Summary Bot\n\n")

            if unreadable_pdf:
                summary = "UNREADABLE PDF"
            elif irrelevant_paper:
                summary = "IRRELEVANT PAPER"

            # Call LLM to gather agent responses
            else:
                out = format_bot(datum,format,question)
                summary = out["formatted_data"]
                if 'NO DATA' not in summary:
                    graph = KG_chain(summary,KG_csv,entities)
                    memory.append(graph['tuples1'])
                    print(summary)
                    print("\n\n")

            # Append data to lists
            all_formatted_data.append(summary)
            all_responses.append(responses)
            all_data.append(datum)
            all_context.append(contexts)

            # Increase question counter
            q_num += 1

        # Save paper data, row-by-row
        save_row(identity,all_formatted_data,output_dir)
        if not irrelevant_paper and 'NO DATA' not in summary:
            KG_save(KG_csv,KG_csv.replace('.csv','.json'))
        paper_num += 1







