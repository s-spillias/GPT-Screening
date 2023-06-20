
#exec(open('../Code/app.py').read())

def generate_text(openAI_key, prompt, n_reviewers, model_to_use):
    openai.api_key = openAI_key
    messages = [{'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': prompt}]
    failed = True
    attempt = 0
    while failed:
        attempt += 1
        if attempt < n_retries:
            try:
                completions = openai.ChatCompletion.create(
                model=model_to_use,
                messages=messages,
                max_tokens=512,
               # logprobs = logprobs,
                n=n_reviewers,
                stop=None,
                temperature=temperature)
                failed = False
            except:
                print('Connection Error - Retrying')
                time.sleep(1*2^attempt)     
        else:    
            continue
   # message = completions.choices.message['content']
    return completions

def get_data(prompt,content,n_reviewers):
    prompt = prompt + "\n\n" + content + '\n\n'
    #print(prompt)
    ## Call OpenAI
    assessments = []
    initial_decisions = []
    final_decisions = []
    decisions = []
    conflicts = []
    rand_string = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
    for r in range(0,n_reviewers):
        bad_answer = True
        while bad_answer: # Force a correctly formatted response.
            # Add in random string for uniqueness
            if rand_seed:
                rand_string = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
            else:
                rand_string = rand_string
         #   print(rand_string)
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
                    #SC_num = thoughts.split("-")[0]
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
                col_decision = "Accept - SC" + f"{SC_num}: " + ScreeningCriteria[int(SC_num)-1]
                col_rationale = "Rationale - SC" + f"{SC_num}: " + ScreeningCriteria[int(SC_num)-1]
                col_thoughts = "Thoughts - SC" + f"{SC_num}: " + ScreeningCriteria[int(SC_num)-1]
                bad_answer = False  
            except:
                print("Bad Parsing...Trying again...")
        # Store outputs
        info_all[r].at[i,col_decision] = decision
        info_all[r].at[i,col_rationale] = rationale
        info_all[r].at[i,col_thoughts] = thoughts
        initial_decision = ["Yes","No"]["No;" in thoughts]
        #print(initial_decision)
        final_decision = ["Yes","No"]["No" in decision]
       # print(final_decision)
       # Show if an AI agent 'changed its mind'
        conflicted = (initial_decision != final_decision)
        conflicts.append(conflicted)
       # print(conflicted)
        initial_decisions.append(final_decision)
        final_decisions.append(initial_decision)
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
            f"only a {responses} "\
            "followed by a semicolon and a single sentence explanation for your reasoning. Like this: "\
            "\nSC: Final Response; One sentence of reasoning."
    return base_prompt


def save_results(screen_name):
    if not os.path.exists('./Output'):
        os.makedirs('./Output')
    file_path = './Output/2a_' + screen_name +'_screen-summary'
    try:
        summary_decisions_new.to_csv(file_path + '.csv', encoding='utf-8', index=True)
    except:
        print("Couldn't Save...is file open?")
    for reviewer in range(len(info_all)):
       # index = 1
        file_path = './Output/2_' + screen_name +'_screened_' + note + "-" + str(reviewer)
        print("Saving at " + file_path + '.csv')
        info_all[reviewer].to_csv(file_path + '.csv', encoding='utf-8', index=True)
