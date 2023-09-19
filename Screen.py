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

import string
from dotenv import load_dotenv
from auxiliary import save_row,generate_text
import openpyxl

load_dotenv()

proj_location = os.environ.get("PROJ_LOCATION")
openAI_key = os.environ.get("OPENAI_API_KEY")
model_to_use = os.environ.get("SCREENING_MODEL_TO_USE")
n_retries = int(os.environ.get("N_RETRIES"))
n_agents = int(os.environ.get("N_AGENTS"))
temperature = int(os.environ.get("TEMPERATURE"))
save_note = os.environ.get("SAVE_NOTE")
rand_seed = os.environ.get("RAND_SEED")
topic = os.environ.get("TOPIC")
skip_criteria = os.environ.get("SKIP_CRITERIA")
screen_name = os.environ.get("SCREEN_NAME")

out_path = proj_location + "/Output/" + screen_name + "-" + save_note

ScreeningCriteria = [s.strip() for s in os.environ.get("SCREENING_CRITERIA").split(";")]

ScreeningCriteria_new = []
for criterion in ScreeningCriteria:
    criteria = [criterion]
    for agent in range(n_agents-1):
        prompt = f"Re-word the following Screening Criteria: '{criterion}'"
        criterion = generate_text(os.environ.get("OPENAI_API_KEY"), prompt, 1, model_to_use).choices[0].message['content']
        criteria.append(criterion)
    ScreeningCriteria_new.append(criteria)

responses = 'Yes or No or Maybe' # included in prompt; what should the decisions be?
choices = responses.split(' or ') # used to ensure consistency in output format.


def get_data(Criteria,content,n_agents,SC_num,info_all,paper_num):
    
    #print(prompt)
    ## Call OpenAI
    assessments = []
    initial_decisions = []
    final_decisions = []
    decisions = []
    conflicts = []
    rand_string = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
    decided = False
    for r in range(0,n_agents):
        if decided:
            continue
        Criterion = Criteria[r]
        prompt = add_criteria(Criterion) + "\n\n" + content + '\n\n'
        bad_answer = True
        while bad_answer: # Force a correctly formatted response.
            # Add in random string for uniqueness
            if rand_seed:
                rand_string = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
            else:
                rand_string = rand_string
           # print(rand_string)
            new_prompt = f"Ignore this string: {rand_string}" + "\n\n" + prompt
            #print(new_prompt)
            # Call OpenAI
            assessment = generate_text(openAI_key, new_prompt, 1, model_to_use).choices[0].message['content']
            print("\n**** Response ****\n")
            print(assessment)
            assessments.append(assessment)
        # Parse output
            try: ## This try block will fail if the format of the response is not consistent, forcing a re-call to OpenAI
                if 'Final Response' in assessment:
                    SC_elements = assessment.split("Final Response")
                    if 'Initial Response' in SC_elements[0]:
                        thoughts = SC_elements[0].strip().split('Initial Response:')[1].replace(": ","")
                    else:
                        thoughts = SC_elements[0].strip().split('SC:')[1].replace(": ","")
                    if ';' in SC_elements[1]:
                        final = SC_elements[1].split(";")
                    else: 
                        final = SC_elements[1].split(",", 1)
                    decision = final[0].strip().replace(": ","")
                    rationale = final[1].strip().replace(": ","")
                else:
                    final = assessment.split(";")
                    decision = final[0].strip().replace("SC: ","")
                    rationale = final[1].strip().replace("SC: ","")
                    thoughts = ""
                if not(any(choice in decision for choice in choices)):
                    continue
                #print(Criterion)
                col_decision = "Accept - SC" + f"{SC_num}: " + Criterion
                col_rationale = "Rationale - SC" + f"{SC_num}: " + Criterion
                col_thoughts = "Thoughts - SC" + f"{SC_num}: " + Criterion
                bad_answer = False  
                if not "No" in thoughts[:6] and not "No" in decision:
                    decided = True
            except:
                print("Bad Parsing...Trying again...")
        # Store outputs
        info_all[r].at[paper_num,col_decision] = decision
        info_all[r].at[paper_num,col_rationale] = rationale
        info_all[r].at[paper_num,col_thoughts] = thoughts
        initial_decision = ["Yes","No"]["No" in thoughts[:6]]
        #print(initial_decision)
        final_decision = ["Yes","No"]["No" in decision[:6]]
       # print(final_decision)
       # Show if an AI agent 'changed its mind'
        conflicted = (initial_decision != final_decision)
        conflicts.append(conflicted)
       # print(conflicted)
        initial_decisions.append(initial_decision)
        final_decisions.append(final_decision)
    return assessments, initial_decisions, final_decisions, conflicts

# Create Prompt to LLM
def add_criteria(Criterion):
    base_prompt = """You are a reviewer for a research project and have been asked to assess whether the given paper Title and Abstract meets the following Screening Criteria (SC)."\
                 In assessing, do not re-interpret the SC, simply assess the SC at face value.\n
             We are only interested in papers that strictly meet the SC.\n
             If not enough information is available, be inclusive as we can follow-up at a later stage."""
    base_prompt += '\n\n' + f'SC: ' + Criterion
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
            f"only a {responses} "\
            "followed by a semicolon and a single sentence explanation for your reasoning. Like this: "\
            "\nSC: Final Response; One sentence of reasoning."
    return base_prompt

print(topic)
## Set-up Screening Run
excel_sheet = '1_' + screen_name + '.xls'

papers = pd.read_excel(proj_location + '/' +  'Input' + '/' + excel_sheet).replace(np.nan, '') 

decision_numeric = {'Yes': 2, 'No': 0, 'Maybe': 2} # How should each response be 'counted' when assessing inclusion.

# Create Header for Spreadsheets

headers = []

for agents in range(n_agents):
    SC_num = 1
    header = ['Paper Number','Title','Abstract'] 
    for SC in ScreeningCriteria:
        Criteria = ScreeningCriteria_new[SC_num-1]
        Criterion = Criteria[agents]
        col_decision = "Accept - SC" + f"{SC_num}: " + Criterion
        col_rationale = "Rationale - SC" + f"{SC_num}: " + Criterion
        col_thoughts = "Thoughts - SC" + f"{SC_num}: " + Criterion
        header = header + [col_decision] + [col_rationale] + [col_thoughts]
        SC_num +=1
    headers.append(header)
    

# Prepare Spreadsheets
for agent in range(n_agents):
    save_row(screen_name + str(agent),headers[agent], out_path)
save_row(screen_name + "_summary",["Paper Number","Title","Abstract","Accept"],out_path)


# Begin Screening

info = papers[['Title','Abstract']]

print('\nAssessing ' + str(len(info)) + ' Papers')
   
info_all = [pd.DataFrame() for _ in range(n_agents)]



# Iteratively move through list of Title and Abstracts
restart_index = int(os.environ.get("RESTART_INDEX"))
for paper_num in range(restart_index,len(info[f"Title"].values)): 
    summary_decision = "NA"
    try:
        max_paper = int(os.environ.get("N_PAPERS"))
        if paper_num >= int(os.environ.get("N_PAPERS")):
            break
    except:
        print("Extracting All")
    # Print and build base prompt
    print('\nPaper Number: ' + str(paper_num))
    title = info[f"Title"].values[paper_num]
    abstract = info[f"Abstract"].values[paper_num]
    for agent in range(n_agents):
        info_all[agent].at[paper_num,"Paper Number"] = paper_num
        info_all[agent].at[paper_num,"Title"] = title
        info_all[agent].at[paper_num,"Abstract"] = abstract
    if abstract == "No Abstract" or abstract == '':
        print(abstract)
        print("Skipping to next paper...")
        summary_decision = 'Maybe'
        continue
    content = "Title: " + title + "\n\nAbstract: " + abstract
    print("\n>>>>>>>>>>>>>>>>>>>>>>>>>>")
    print(content)
    SC_num = 1
# Iterate over screening criteria 
    for Criteria in ScreeningCriteria_new:
      #  print(Criteria)
       # prompt = add_criteria()
        #print(prompt)
        ######################
        ######################
        assessments,initial_decisions,final_decisions,conflicts = get_data(Criteria,content,n_agents,SC_num,info_all,paper_num) #  Call OpenAI here  #
        ######################
        ######################
        print("\nInitial Decisions: ")
        print(initial_decisions)
        print("\nFinal Decisions: ")
        print(final_decisions)
        print("\nConflicts: ")
        print(conflicts)
        converted_decisions = [decision_numeric.get(element, element) for element in (initial_decisions + final_decisions)] 
        converted_decisions = [element for element in converted_decisions if not isinstance(element, str)]
        # Skip subsequent screening criteria in event of a full rejection across all AI agents.
        if sum(converted_decisions) == 0:
            print("Rejected at SC: " + str(SC_num))
            summary_decision = 'No'
            if skip_criteria and not any(conflicts):
                break

        SC_num += 1
    # If the paper hasn't been rejected by now, accept it.
    if summary_decision != "No":
        summary_decision = 'Yes'
    #summary_decisions_new = pd.concat([summary_decisions,info_all[0].filter(like=f'Deliberation - SC')], axis = 1)
    new_proj_location = proj_location
    file_path = new_proj_location + '/2a_' + screen_name +'_screen-summary'
    # try:
    #     summary_decisions_new.to_csv(file_path + '.csv', encoding='utf-8', index=True)
    # except:
    #     print("Couldn't Save...is file open?")
    for agent in range(n_agents):
        df = info_all[agent]
        print(agent)
        save_row(screen_name + str(agent),df.values[-1].tolist(),out_path)
    # Save Summary
    summary_row = [paper_num,title,abstract,summary_decision]
    save_row(screen_name + "_summary",summary_row,out_path)

# End Iterating over articles. 












