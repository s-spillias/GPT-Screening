import os
import xlrd
import glob
import pandas as pd 
#pd.options.mode.chained_assignment = None  # default='warn'
import re
from nltk import agreement
import time

# Meta-Parameters
synthesize_gpt = True
openAI_key = "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"
model_to_use = "gpt-3.5-turbo-0301"
temperature = 0.0
n_retries = 10
# Import Functions
exec(open('0_Functions.py').read())

dir = "CBFM"
#topic = "'The barriers and benefits of Community-Based Fisheries Management in the Pacific'"
#ScreeningCriteria = [
#    "Is it likely that the Title or Abstract are referring to one of the following: Cook Islands, Federated States of Micronesia, Fiji, Kiribati, Marshall Islands, Nauru, Niue, Palau, Papua New Guinea, Samoa, Solomon Islands, Tonga, Tuvalu, Vanuatu",
##    "Is it likely that the Title and Abstract summarise a paper related to fisheries and/or marine resource management?",
 #   "Is it likely that the Title and Abstract summarise a paper related to community-based management? The definition of community-based management here is “an approach to fisheries management that gives coastal communities and fishers primary responsibility for managing their coastal resources”",
   # "Is it likely that the Title and Abstract summarise a paper that will contain information on either the benefits or barriers to community-based fisheries management? Accept the paper if either barriers or benefits are likely to be discussed."
  #  ]
n_reviewers = 5
screen_name = 'remainder'
d = {'Yes': 2, 'No': 0, 'Maybe': 2}

all_files = glob.glob(dir + "/*_" + screen_name + "_screened*")

raw = []
data = []
all_votes = []
title_included = []
decisions = pd.DataFrame()
n_included = []
for file in all_files:
   screen = pd.read_csv(file).fillna('')
   titles = screen['Title']
   abstracts = screen['Abstract']
   raw.append(screen.drop(columns =['Title','Abstract','Unnamed: 0']))
   included = screen[~screen['Accept'].str.contains('No')]['Title'].tolist()
   n = len(included)
   SC_decisions = screen.filter(regex = 'Accept - SC').applymap(lambda x: d.get(x, x))
   decisions = pd.concat([decisions,SC_decisions],axis = 1)
   ScreeningCriteria = [item.replace('Accept - SC',"") for item in SC_decisions.axes[1].tolist()]
   dat = screen['Accept'].map(d).tolist()
   votes = pd.concat([titles,pd.DataFrame(dat)], axis =1)
   #if 'all_votes' in locals() or 'all_votes' in globals():
   all_votes.append(votes[0]/2)
   data.append(dat)
   n_included.append(n)
   title_included.append(included)

all_votes = [sum(items) for items in zip(*all_votes)]
# Include All Studies with at least one 'Accept' [UNION]
union_set = set(title_included[0])
for l in title_included[1:]:
    union_set = union_set.union(set(l))

# Include Only Studies with at all 'Accept's [Intersection]
inter_set = set(title_included[0]).intersection(*[set(list) for list in title_included[1:]])

# Disagreement Papers
diff_set = list(set(union_set).symmetric_difference(set(inter_set)))

# Number of Votes
all_votes = pd.DataFrame(all_votes)
all_votes.columns =['Num_Yes']

# Re-create metadata spine
out = pd.concat((titles,abstracts,all_votes), axis = 1)

# ID which to include
out.loc[out['Title'].isin(inter_set), 'Include'] = 'Yes'
out.loc[out['Title'].isin(diff_set), 'Include'] = 'Maybe'
out.loc[~out['Title'].isin(union_set), 'Include'] = 'No'

# Identify most disputed SC
#for i in range(1,1+len(ScreeningCriteria)):
#    sum_columns = decisions.filter(like=f'Accept - SC' + str(i))
#    sum_columns.to_csv(f'SC{i}.csv', encoding='utf-8', index=True)
#    decisions['Agreement - SC' + str(i)] = (abs(sum_columns.sum(axis=1,skipna=True) - (n_reviewers/2))/(n_reviewers/2))
#decisions.apply(lambda row: row['A'] + row['B'], axis=1)
agree = screen[['Title','Abstract']]
#agree = pd.concat([screen[['Title','Abstract']],decisions.filter(like='Agreement')],axis = 1)

out = pd.merge(out, agree, on =['Title','Abstract'])

raw = pd.concat(raw, axis=1)

out = pd.concat([out,raw],axis =1)
last_decision = []
last_rationale = []
last_thoughts = []
for i in range(0,len(titles)):
    title = out['Title'][i]
    Num_Yes = out['Num_Yes'][i]
    if Num_Yes == n_reviewers:
        last_decision.append("Yes")
        last_rationale.append('Agreement')
        last_thoughts.append('NA')
    elif Num_Yes == 0:
        last_decision.append("No")
        last_rationale.append('Agreement')
        last_thoughts.append('NA')
    else:
            print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
            print('Synthesizing: Paper: ' + str(i))
            print(title)
            SC_num = 0
            SC_decision = []
            for SC in ScreeningCriteria:
                print("\n")
                bad_response = True
                while bad_response:
                    print(SC)
                    SC_num += 1
                    decisions = out[out['Title']==title].filter(like=f'Accept - SC{SC_num}').values.tolist()[0]
                    reasons = out[out['Title']==title].filter(like=f'Rationale - SC{SC_num}').values.tolist()[0]
                    responses = 'Yes or No'
                    if synthesize_gpt:
                        assessment = synth_decisions(decisions,reasons,responses,SC).choices[0].message['content']
                        print(assessment)
                    else:
                        assessment = 'dummy'
                    try:
                        elements = assessment.split("Final Response")
                        if 'Initial Response' in elements[0]:
                            thoughts = elements[0].strip().split('Initial Response:')[1].replace(": ","")
                        else:
                            thoughts = elements[0].strip().split('SC:')[1].replace(": ","")
                        #SC_num = thoughts.split("-")[0]
                        final = elements[1].split(";")
                        decision = final[0].strip().replace(": ","")
                        rationale = final[1].strip().replace(": ","")
                        SC_decision.append(decision)
                        bad_response = False
                    except:
                        continue
            if any('No' in element for element in SC_decision):
                print('Include? No')
                last_decision.append('No')
            else:
                last_decision.append('Yes')
                print('Include? Yes')


file_path = dir + '/2a_' + screen_name + '_summary.csv'

outcomes = pd.DataFrame()
outcomes['Final Decision'] = last_decision
#outcomes['Final Decision - Rationale'] = last_rationale
#outcomes['Final Decision - Thoughts'] = last_thoughts

out = pd.concat([outcomes,out], axis = 1)

print("Saving at " + file_path)
out.to_csv(file_path, encoding='utf-8', index=True)

# Save data for stats
pd.DataFrame(data).transpose().to_csv(dir + '/2a_' + screen_name + '_kappa-AI-reviewers.csv', encoding='utf-8', index=False,header=False)

# Ask GPT to synthesize across reviewers
out['Final Decision'].map(d).to_csv(dir + '/2a_' + screen_name + '_k-synth-gpt.csv', encoding='utf-8', index=False,header=False)
# Include all papers where at least one reviewer says yes
out['Include'].map(d).to_csv(dir + '/2a_' + screen_name + '_k-synth-unify.csv', encoding='utf-8', index=False,header=False)
