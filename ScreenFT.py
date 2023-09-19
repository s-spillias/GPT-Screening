
import openai
import os
from dotenv import load_dotenv
from auxiliary import save_row
import pandas as pd
import json
from time import sleep
#from fine_tune import create_user_message

load_dotenv()
openai.api_key = os.environ.get("OPENAI_API_KEY")

proj_location = os.environ.get("PROJ_LOCATION")

with open(proj_location + "/proj_details.json", "r") as json_file:
    proj_details = json.load(json_file)

topic = proj_details["TOPIC"]
ScreeningCriteria = proj_details["SCREENING_CRITERIA"]
prompt = proj_details["PROMPT"]
model_to_use = proj_details["SCREENING_MODEL_TO_USE"]
print(model_to_use)

system_message = prompt + " " + str(ScreeningCriteria)

def create_user_message(row):
    return f"""Title: {row['Title']}\n\nAbstract: {row['Abstract']}\n\nAccept?: """

save_note = os.environ.get('SAVE_NOTE')

out_path = proj_location + "/Output/" + save_note
save_row("summary",["Paper Number","Title","Abstract","Human Accept",model_to_use],out_path)


df = pd.read_csv(proj_location + "/fine_tune.csv")

for row_num in range(int(os.environ.get("RESTART_INDEX")),len(df)):
    try:
        max_paper = int(os.environ.get("N_PAPERS"))
        if row_num >= int(os.environ.get("N_PAPERS")):
            break
    except:
        print("Screening All")
    test_row = df.iloc[row_num]
    title = test_row["Title"]
    abstract = test_row["Abstract"]
    human_accept = test_row["Accept"]
    print("Paper - " + str(row_num))
    print(title +"\n")
    print(abstract+"\n")
    print("\n")
    test_messages = []
    test_messages.append({"role": "system", "content": system_message})
    user_message = create_user_message(test_row)
    test_messages.append({"role": "user", "content": create_user_message(test_row)})

    trying = True
    while trying:
        try:
            response = openai.ChatCompletion.create(
                model=model_to_use, messages=test_messages, temperature=0, max_tokens=500
            )
            trying = False
        except:
            print("Query Failed. Retrying...")
            sleep(5)

    answer = response["choices"][0]["message"]["content"]
    print(answer)
    save_row("summary",[row_num,title,abstract,human_accept,answer],out_path)