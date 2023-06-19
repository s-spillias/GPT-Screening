import os
import xlrd
import pandas as pd 
pd.options.mode.chained_assignment = None  # default='warn'
import re
import numpy as np
#from time import time
import time
import random
import string

#start = time()

debug = False

pdf_location = "CBFM"
screen_name = 'redo'
exec(open(pdf_location + '/set-up.py').read())


# Pre- Remainder Account Balance: $17.54 / $120.00
#Post - Remainder Account Balance: $28.65 / $120.00

excel_sheet = '1_' + screen_name + '.xls'

scenarios = [#"scen_basic",
             "scen_consensus",
             "scen_consensus_norand",
            # "scen_reflection","scen_comittee_reflection","scen_consensus_reflection"
             ]

comittee_size = 5
max_deliberations = 3
skip_criteria = True
synthesize_gpt = False

papers = pd.read_excel(pdf_location + '/' + excel_sheet).replace(np.nan, '')  

if debug: 
    n_studies = 5
else:
    n_studies = len(papers)

responses = 'Yes or No or Maybe'
d = {'Yes': 2, 'No': 0, 'Maybe': 2}

choices = responses.split(' or ') # used to ensure consistency in output format.

# Meta-Parameters
openAI_key = "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"
model_to_use = "gpt-3.5-turbo-0301"
#model_to_use = "text-davinci-003"
temperature = 0
#top_p = 0.1
#best_of = n_reviewers + 1
n_retries = 10
# Import Functions
exec(open('0_Functions.py').read())

# Begin Screening

for scen in scenarios:
    print("\nInitializing Scenario:" + scen)

    if scen == "scen_basic":
        reflection = False
        n_reviewers_base = 1
        consensus = False
        rand_seed = True
    elif scen == "scen_reflection":
        reflection = True
        n_reviewers_base = 1
        consensus = False
        rand_seed = True
    elif scen == "scen_comittee_reflection":
        reflection = True
        n_reviewers_base = comittee_size
        consensus = False
        rand_seed = True
    elif scen == "scen_consensus_reflection":
        reflection = True
        n_reviewers_base = comittee_size
        consensus = True
        rand_seed = True
    elif scen == "scen_consensus":
        reflection = False
        n_reviewers_base = comittee_size
        consensus = True
        rand_seed = True
    elif scen == "scen_consensus_norand":
        reflection = False
        n_reviewers_base = comittee_size
        consensus = True
        rand_seed = False
    info = papers[['Title','Abstract']]
    info = info[0:n_studies] # For Debugging
    print('\nAssessing ' + str(len(info)) + ' Papers')
    info[f"Accept"] = "NA"    
    info_all = [info.copy() for _ in range(comittee_size)]
    summary_decisions = info
    for i in range(0,len(info[f"Title"].values)): # Iteratively move through list of Title and Abstracts
        relevance = 0
        if i % 101 == 99:
            print('Saving Intermediate Results...')
            summary_decisions_new = pd.concat([summary_decisions,info_all[0].filter(like=f'Deliberation - SC')], axis = 1)
            save_results(screen_name + '_int')
        if i % 10 == 0:
            print('Saving Intermediate Results...')
            summary_decisions_new = pd.concat([summary_decisions,info_all[0].filter(like=f'Deliberation - SC')], axis = 1)
            if debug:
                 new_pdf_location = pdf_location + "/debug"
            else:
                new_pdf_location = pdf_location
            file_path = new_pdf_location + '/2a_' + screen_name +'_screen-summary'
            try:
                summary_decisions_new.to_csv(file_path + '.csv', encoding='utf-8', index=True)
            except:
                print("Couldn't Save...is file open?")
        any_max_delib = False
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
        SC_deliberations = []
        n_reviewers = n_reviewers_base
        for Criteria in ScreeningCriteria:
            SC_relevance = 0
            max_delib_reached = False
            disagreement = True
            num_deliberations = 0
            while disagreement:
                prompt = add_criteria(Criteria)
                #print(prompt)
                assessments,decisions, conflicts = get_data(prompt,content,n_reviewers)
                if reflection:
                    print("\nFinal responses")
                else:
                    print("\nInitial responses")
                print("\nDecisions: ")
                print(decisions)
                converted_decisions = [d.get(element, element) for element in decisions] 
                converted_decisions = [element for element in converted_decisions if not isinstance(element, str)]
                num_deliberations += 1
                if consensus: # flag for 'consensus' scenario; to prevent consensus from being required
                   disagreement = False
                for conflicted in conflicts:
                    if conflicted:
                        SC_relevance += 0.5
                        print("Conflicted")
                    #print(f"Uncertainty at: {uncertainty}")
                   # disagreement = True
                   # n_reviewers = comittee_size
                   # continue
                if all(element == converted_decisions[0] for element in converted_decisions):
                    print("\nConsensus achieved after: " + str(num_deliberations))
                    disagreement = False
                else:
                    print('Consensus Failed after: ' + str(num_deliberations))
                    if num_deliberations == max_deliberations:
                        print("Reached Max Deliberation...")
                        max_delib_reached = True
                        any_max_delib = True
                        col_max_deliberation = "Max Deliberation - SC" + f"{SC_num}: " + Criteria
                        for r in range(0,n_reviewers):
                            info_all[r].at[i,col_max_deliberation] = 'Yes'
                        disagreement = False
                        continue
            col_deliberation = "Deliberation - SC" + f"{SC_num}: " + Criteria
            for r in range(0,n_reviewers):
                info_all[r].at[i,col_deliberation] = num_deliberations
            SC_num += 1
            SC_deliberations.append(num_deliberations)

            if sum(converted_decisions) == 0:
                print("Rejected at SC: " + str(SC_num -1))
                summary_decisions.at[i,'Accept'] = 'No'
                if skip_criteria and not any(conflicts):
                    break
            else:
                SC_relevance += sum(converted_decisions)/2
                SC_relevance = min(comittee_size,SC_relevance)
            relevance += SC_relevance
        if summary_decisions.loc[i,'Accept'] == "NA" and any_max_delib:
            summary_decisions.at[i,'Accept'] = 'Maybe'
        elif summary_decisions.loc[i,'Accept'] == "NA":
            summary_decisions.at[i,'Accept'] = 'Yes'
        relevance_normalized = relevance/((SC_num -1)*comittee_size)
        summary_decisions.at[i,'Relevance'] = relevance_normalized
        print(f"Relevance: {relevance_normalized}")
    summary_decisions_new = pd.concat([summary_decisions,info_all[0].filter(like=f'Deliberation - SC')], axis = 1)

    save_results(screen_name + "_" + scen)

