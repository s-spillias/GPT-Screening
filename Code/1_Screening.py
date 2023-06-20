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


## Set meta-parameters
debug = False # Run fewer articles for debugging purposes

n_reviewers = 2 # Number of AI agents to independently ask

skip_criteria = True # Will skip remaining screening criteria if one fails across all AI agents

rand_seed = True # Insert random string into prompts for uniqueness

proj_location = "CBFM" # Directory name of project.

screen_name = 'pilot' # Name of spreadsheet with Abstract and Title *without extensions

note = '' # This will append a note to the output files

openAI_key = "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" # Insert your OpenAI API key

model_to_use = "gpt-3.5-turbo-0301" # Currently only set-up for "gpt-3.5-turbo-0301"

temperature = 0 # increasing this number will lead to less 'truthful' responses

n_retries = 10 # Number of times to re-query OpenAI in event of disconnection

save_frequency = 3 # How often to save intermediate results.

exec(open(proj_location + '/set-up.py').read()) # Import Screening Criteria Text


## Set-up Screening Run
excel_sheet = '1_' + screen_name + '.xls'

papers = pd.read_excel(proj_location + '/' + excel_sheet).replace(np.nan, '')  

if debug: 
    n_studies = 5
else:
    n_studies = len(papers)

responses = 'Yes or No or Maybe' # included in prompt; what should the decisions be?
decision_numeric = {'Yes': 2, 'No': 0, 'Maybe': 2} # How should each response be 'counted' when assessing inclusion.

choices = responses.split(' or ') # used to ensure consistency in output format.

# Import Functions
exec(open('Code/0_Functions.py').read())

# Begin Screening

info = papers[['Title','Abstract']]
info = info[0:n_studies] # For Debugging
print('\nAssessing ' + str(len(info)) + ' Papers')
info[f"Accept"] = "NA"    
info_all = [info.copy() for _ in range(n_reviewers)]
summary_decisions = info

# Iteratively move through list of Title and Abstracts
for i in range(0,len(info[f"Title"].values)): 
    if i % save_frequency == 0: # Save intermediate results in case of disconnection or other failure.
        print('Saving Intermediate Results...')
        summary_decisions_new = pd.concat([summary_decisions,info_all[0].filter(like=f'Deliberation - SC')], axis = 1)
        new_proj_location = proj_location
        file_path = new_proj_location + '/Output/2a_' + screen_name +'_screen-summary'
        try:
            save_results(screen_name)
        except:
            print("Couldn't Save...is file open?")
# Print and build base prompt
    print('\nPaper Number: ' + str(i))
    title = info[f"Title"].values[i]
    abstract = info[f"Abstract"].values[i]
    if "No Abstract" in abstract:
        print(abstract)
        print("Skipping to next paper...")
        summary_decisions.at[i,'Accept'] = 'Maybe'
        continue
    content = "Title: " + title + "\n\nAbstract: " + abstract
    print("\n>>>>>>>>>>>>>>>>>>>>>>>>>>")
    print(content)
    SC_num = 1
# Iterate over screening criteria 
    for Criteria in ScreeningCriteria:
        prompt = add_criteria(Criteria)
        #print(prompt)
######################
######################
        assessments,initial_decisions,final_decisions,conflicts = get_data(prompt,content,n_reviewers) #  Call OpenAI here  #
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
            summary_decisions.at[i,'Accept'] = 'No'
            if skip_criteria and not any(conflicts):
                break

        SC_num += 1
# If the paper hasn't been rejected by now, accept it.
    if summary_decisions.loc[i,'Accept'] == "NA":
        summary_decisions.at[i,'Accept'] = 'Yes'
# End Iterating over articles. 

summary_decisions_new = summary_decisions
# Save results
save_results(screen_name)

