# Author: Scott Spillias
# Email: scott.spillias@csiro.au

## Import Packages
import os
import xlrd
import pandas as pd 
pd.options.mode.chained_assignment = None  # default='warn'
import re
import numpy as np
import time
import random
import openai
import string
import csv
from dotenv import load_dotenv
from auxiliary import save_sheet, save_row
from itertools import zip_longest

load_dotenv()

models = ['gpt-4-1106-preview',
          "gpt-3.5-turbo-0613",
          #"gpt-3.5-turbo-0301",
          "google-pro"
          
          ]
scenarios = [#"baseline_rand_seed", # set temp to 0.0, top-p to 0, and include random string
             "temperature0", #set temperature to 0.0
             #"temperature", # set temperature to 1.0
             #"top_p", # set top-p to 0.2
             #"set_seed" # create random seed. NB: requires openai version > 1.0
             ]
prompts = ["default",
           "modified_SC2"]

n_retries = 5
restart_index = 0
topic = "Benefits and Barriers to Community Based Fisheries Management"
skip_criteria = True
n_papers = "ALL"

proj_location = "CBFM"
debug = False
openAI_key = os.environ.get("OPENAI_API_KEY")
google_key = os.environ.get("GOOGLE_KEY")
n_agents = 3

global set_seed

file_path = proj_location + '/ScreeningCriteria.csv'  



responses = 'Yes or No or Maybe' # included in prompt; what should the decisions be?
choices = responses.split(' or ') # used to ensure consistency in output format.

def generate_text(openAI_key, prompt, n_reviewers, model_to_use):
    if model_to_use == 'gpt-4-1106-preview':
        openai.api_type = "azure"
        openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT") 
        openai.api_key = os.getenv("AZURE_OPENAI_KEY")
        openai.api_version = "2023-07-01-preview"
        model = "firstcontact-gpt4-turbo"
    else:
        openai.api_key = os.environ.get("OPENAI_API_KEY")
        openai.api_type = "openai"
        model = model_to_use
    messages = [{'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': prompt}]
    failed = True
    attempt = 0
    while failed:
        attempt += 1
        if attempt < n_retries:

            try:
                if set_seed:
                    seed = int(''.join(random.choice(string.digits) for _ in range(10)))
                else:
                    seed = 42
                completions = openai.ChatCompletion.create(
                    model=model,
                    engine = model,
                    messages=messages,
                    max_tokens=512,
                    #seed = seed,
                # logprobs = logprobs,
                    n=n_reviewers,
                    stop=None,
                    temperature=temperature)
                failed = False
            except:
                print('Connection Error - Retrying')
                time.sleep(1*2^attempt)     
        else:    
            break
   # message = completions.choices.message['content']
    return completions

def collate_data(list1,list2,list3):
        
    max_length = max(len(list1), len(list2), len(list3))

    result = [item for sublist in zip_longest(list1, list2, list3, fillvalue=None) for item in sublist]
    return result

def get_data(Criterion,content,n_agents,SC_num,info_all,paper_num):
    #print(prompt)
    ## Call OpenAI
    assessments = []
    initial_decisions = []
    final_decisions = []
    decisions = []
    conflicts = []
    rand_string = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
    decided = False
    for agent in range(0,n_agents):
        print(agent)
        if decided:
            continue
        prompt = add_criteria(Criterion) + "\n\n" + content + '\n\n'
        bad_answer = True
        while bad_answer: # Force a correctly formatted response.
            # Add in random string for uniqueness
            if rand_seed:
                rand_string = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
            else:
                rand_string = rand_string
            # print(rand_string)
            new_prompt = f"Ignore this string: {rand_string}" + "\n\n" + prompt + content
            #print(new_prompt)
            # Call OpenAI
            try: 
                assessment = generate_text(openAI_key, new_prompt, 1, model_to_use).choices[0].message.content
            except:
                assessment = "No Data"
                bad_answer = False
            print("\n**** Response ****\n")
            print(assessment)
            assessments.append(assessment)
            pattern = r'\b(Yes|No|Maybe)\b'

            matches = re.findall(pattern, assessment)
        # Parse output
            try: ## This try block will fail if the format of the response is not consistent, forcing a re-call to OpenAI
                final_decision = matches[-1]
                initial_decision = matches[0]
                thoughts = assessment
                #print(Criterion)
                col_decision = "Final Decision - SC" + f"{SC_num}: " + Criterion
                col_initial = "Initial Decision - SC" + f"{SC_num}: " + Criterion
                col_thoughts = "Thoughts - SC" + f"{SC_num}: " + Criterion
                if not "No" in initial_decision[:6] and not "No" in final_decision:
                    decided = True
                bad_answer = False 
            except:
                print("Bad Parsing...Trying again...")
        # Store outputs
        info_all[agent].loc[paper_num, ['Paper Number',"Title", "Abstract"]] = [paper_num, title, abstract] if title and abstract else 'NO DATA'
        if not bad_answer:
            info_all[agent].loc[paper_num, col_decision] = final_decision 
            info_all[agent].loc[paper_num, col_initial] = initial_decision 
            info_all[agent].loc[paper_num, col_thoughts] = thoughts 
        conflicted = (initial_decision != final_decision)
        conflicts.append(conflicted)
        initial_decisions.append(initial_decision)
        final_decisions.append(final_decision)
    return assessments, initial_decisions, final_decisions, conflicts

# Create Prompt to LLM
def add_criteria(Criteria):
    base_prompt = "You are a reviewer for a research project and have been asked to assess whether the "\
             "given paper Title and Abstract meets the following Screening Criteria (SC)."\
                 " In assessing, do not re-interpret the SC, simply assess the SC at face value.\n"\
             "We are only interested in papers that strictly meet the SC.\n"\
             "If not enough information is available, be inclusive as we can follow-up at a later stage."
    base_prompt += '\n\n' + f'SC: ' + Criteria 
    base_prompt += '\n\n' + f"Task: Given the following Title and Abstract, respond"\
            f" to the Screening Criteria (SC) with the following elements, "\
            "Initial Response, Reflection on Initial Response, and Final Response."\
            " Here is an example of how your response should look:\n"\
            "Format: \n"\
            "SC -\n"\
            "Initial Response: Only respond with a Yes or No; Short explanation as rationale.\n"\
            "Reflection: Is the Initial Response correct? Be concise.\n"\
            "Final Response: Strictly only respond with a Yes or No; Short explanation based on reflection. "\
            "\nInitial Response and Final Response should consist of "\
            f"only a Yes or No or Maybe "\
            "followed by a semicolon and a single sentence explanation for your reasoning. Like this: "\
            "\nSC: Final Response; One sentence of reasoning."
    return base_prompt

# def save_results(screen_name,info_all):
#     if debug:
#         new_proj_location = proj_location + "/debug"
#     else:
#         new_proj_location = proj_location + '/Output'
#     if not os.path.exists(new_proj_location):
#         os.makedirs(new_proj_location)
#     file_path = new_proj_location + '/2a_' + screen_name +'_screen-summary'
#     try:
#         summary_decisions_new.to_csv(file_path + '.csv', encoding='utf-8', index=True)
#     except:
#         print("Couldn't Save...is file open?")
#     for reviewer in range(len(info_all)):
#         index = 1
#         file_path = new_proj_location + '/2_' + screen_name +'_screened_' + save_note + "-" + str(index)
#         while os.path.isfile(file_path + '.csv'):
#             file_path = file_path.split("-")[0] + "-" + str(index)
#             index += 1
#         print("Saving at " + file_path + '.csv')
#         try:
#             info_all[reviewer].to_csv(file_path + '.csv', encoding='utf-8', index=True)
#         except:
#             info_all[reviewer].to_csv(file_path + 'e.csv', encoding='utf-8', index=True)



print(topic)
## Set-up Screening Run
excel_sheet = '1_' + "all" + '.xls'

papers = pd.read_excel(proj_location + '/' +  'Input' + '/' + excel_sheet).replace(np.nan, '') 

if debug: 
    n_studies = 3
else:
    n_studies = len(papers)

decision_numeric = {'Yes': 2, 'No': 0, 'Maybe': 2} # How should each response be 'counted' when assessing inclusion.





for iteration in range(0,1):
    for prompt_type in prompts:
        ScreeningCriteria = []  

        with open(file_path, 'r',encoding='utf-8-sig') as file:
            reader = csv.reader(file)
            
            for row in reader:
                if row:  # Check if the row is not empty
                    ScreeningCriteria.append(row[0]) 
        if prompt_type == "modified_SC2":
            ScreeningCriteria[2] = ScreeningCriteria[2].replace(" Exclude if there is a focus on co-management.",'')

        for model_to_use in models:
            for screen_name in scenarios:
                summary_decision = None
                assessments,initial_decisions,final_decisions,conflicts = None, None,None,None
                if screen_name == "baseline_rand_seed":
                    rand_seed = True
                    set_seed = False
                    temperature = 0
                    top_p = 1
                elif screen_name == "temperature":
                    rand_seed = False
                    set_seed = False
                    temperature = 1
                    top_p = 1
                elif screen_name == "temperature0":
                    rand_seed = False
                    set_seed = False
                    temperature = 0
                    top_p = 1
                elif screen_name == "top_p":
                    rand_seed = False
                    set_seed = False
                    temperature = 1
                    top_p = 0.2
                elif screen_name == "set_seed":
                    rand_seed = False
                    set_seed = True
                    temperature = 0
                    top_p = 0
                else:
                    raise(KeyError)
                
                headers = []
                for agents in range(n_agents):
                    SC_num = 1
                    header = ['Title','Abstract','Paper Number'] 
                    for SC in ScreeningCriteria:
                        Criterion = ScreeningCriteria[SC_num-1]
                        col_decision = "Final Decision - SC" + f"{SC_num}: " + Criterion
                        col_rationale = "Initial Decision - SC" + f"{SC_num}: " + Criterion
                        col_thoughts = "Thoughts - SC" + f"{SC_num}: " + Criterion
                        header = header + [col_decision] + [col_rationale] + [col_thoughts]
                        SC_num +=1
                    headers.append(header)

                new_proj_location = proj_location + '/AI_Output'
                if not os.path.exists(new_proj_location):
                    os.makedirs(new_proj_location)
                out_path = new_proj_location + '/December/' + model_to_use + '/' + prompt_type + '_' + screen_name + str(iteration)

                
                info = papers[['Title','Abstract']]
                info = info[0:n_studies] # For Debugging
                print('\nAssessing ' + str(len(info)) + ' Papers')
                #info[f"Accept"] = "NA"    

                info_all = [info.copy() for _ in range(n_agents)]
                summary_decisions = info

                summary_row = ["Paper Number","Title","Abstract","Summary Decision"]
                save_row(screen_name + "_summary",summary_row,out_path)
                # Prepare Spreadsheets
                for agent in range(n_agents):
                    save_row(screen_name + str(agent),headers[agent], out_path)
                    # Begin Screening
                
                # Iteratively move through list of Title and Abstracts
                
                try:
                    int(n_papers)
                except:
                    n_papers = len(info)

                for paper_num in range(restart_index,int(n_papers)): 
                    # if paper_num % 10 == 0: # Save intermediate results in case of disconnection or other failure.
                    #     print('Saving Intermediate Results...')
                    #     summary_decisions_new = pd.concat([summary_decisions,info_all[0].filter(like=f'Deliberation - SC')], axis = 1)
                    #     if debug:
                    #             new_proj_location = proj_location + "/debug"
                    #     else:
                    #         new_proj_location = proj_location
                    #     file_path = new_proj_location + '/2a_' + screen_name +'_screen-summary'
                    #     try:
                    #         summary_decisions_new.to_csv(file_path + '.csv', encoding='utf-8', index=True)
                    #     except:
                    #         print("Couldn't Save...is file open?")
                    # Print and build base prompt
                    print('\nPaper Number: ' + str(paper_num))
                    title = info[f"Title"].values[paper_num]
                    abstract = info[f"Abstract"].values[paper_num]
                    if "No Abstract" in abstract:
                        print(abstract)
                        print("Skipping to next paper...")
                        summary_decisions.at[paper_num,'Accept'] = 'Maybe'
                        continue
                    content = "Title: " + title + "\n\nAbstract: " + abstract
                    print("\n>>>>>>>>>>>>>>>>>>>>>>>>>>")
                    print(content)
                    SC_num = 1

                    # Iterate over screening criteria 
                    for Criterion in ScreeningCriteria:
                        converted_decisions = None
                        #prompt = add_criteria(Criteria)
                        #print(prompt)
                        ######################
                        ######################
                        assessments,initial_decisions,final_decisions,conflicts = get_data(Criterion,content,n_agents,SC_num,info_all,paper_num) #  Call OpenAI here  #
                        #save_info = collate_data(initial_decisions, final_decisions, assessments)
                        ######################
                        ######################
                        print("\nInitial Decisions: ")
                        print(initial_decisions)
                        print("\nFinal Decisions: ")
                        print(final_decisions)
                        #print("\nConflicts: ")
                        #print(conflicts)
                        converted_decisions = [decision_numeric.get(element, element) for element in (initial_decisions + final_decisions)] 
                        converted_decisions = [element for element in converted_decisions if not isinstance(element, str)]
                        # Skip subsequent screening criteria in event of a full rejection across all AI agents.
                        if sum(converted_decisions) == 0:
                            print("Rejected at SC: " + str(SC_num))
                            summary_decision = 'No'
                            if skip_criteria:
                                break
                        else:
                            summary_decision = "Yes"
                        SC_num += 1
                    # If the paper hasn't been rejected by now, accept it.
                    # End Iterating over articles. 
                    summary_row = [paper_num,title,abstract,summary_decision]
                    save_row(screen_name + "_summary",summary_row,out_path)
                    #summary_decisions_new = summary_decisions
                    # Save results

                    i=0
                    for agent in range(len(info_all)): 
                        print(agent)
                        try:
                            save_info = info_all[agent].iloc[paper_num,:].tolist()
                            #save_info = [x for x in save_info if x == x]
                            #print(save_info)
                            save_row(screen_name + str(i),save_info,out_path)
                        except:
                            print("no data")
                        i+=1




