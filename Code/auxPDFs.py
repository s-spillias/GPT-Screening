### Set-Up and Run Coding

# Set-Up
import os, fnmatch
import shutil
import pandas as pd

def find(pattern, path):
    result = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result

# Copy pdf to target
# Either target urls, or pdfs.
url = ''#"https://www.oecd.org/australia/34427707.pdf"

# ID all pdfs in target folder 

citations = [x.split('\\')[-1] for x in all_files]
citations = [x.split('.pdf')[0] for x in citations]
# Import Main Function

def generate_answer(question,openAI_key):
    topn_chunks = recommender(question)
    prompt = ""
    prompt += 'Study:\n\n'
    for c in topn_chunks:
        prompt += c + '\n\n'
        
    prompt += base_prompt
    prompt += f"Instructions: Extract {prompt_type[question]} data from the study provided according the the Query. "
    prompt += f"Data Format: {data_format[prompt_type[question]]}"
    prompt += f"Query: {question}\nAnswer:"

    answer = generate_text(openAI_key, prompt, n_reviewers, model_to_use)
    return answer

exec(open('Code/app.py').read())

def respond():
    response = question_answer(url, file, question,openAI_key).choices[0].message['content']
    print('\n' + response + '\n')
    if 'No Relevant Data' in response:
        r_split = ["NA"]*2
    else:
        r_split = response.split("Context")
    file_data.append(r_split[0])
    file_data_df = pd.DataFrame([file_data])
    file_context.append(r_split[1])
    file_context_df = pd.DataFrame([file_context])
    return file_data_df, file_context_df
all_data = pd.DataFrame()
all_context = pd.DataFrame()


for file in all_files:
    print("\n>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n")
    print(file)
    file_data = []
    file_context = []
    # Remove previous file
    for i in find('corpus*', os.getcwd()):
        os.remove(i)
    # Add in new file
    shutil.copy2(file,'corpus.pdf')
    # Loop Through Questions
    for question in all_questions:
        print(">>>>>>>>")
        print(question)
        print(">>>>>>>>")
        ### Here is the Call to the LLM
        try:
           out = respond()
        except:
           out = respond()
    # Append Responses
    all_data = pd.concat([all_data,out[0]], ignore_index=True)
    all_context = pd.concat([all_context,out[1]], ignore_index=True)

all_data_df = pd.DataFrame(all_data.to_numpy(),citations,all_questions)
all_context_df = pd.DataFrame(all_context.to_numpy(),citations,all_questions)

recommender = SemanticSearch()
topn_chunks = recommender(question)
for c in topn_chunks: 
    print(c)