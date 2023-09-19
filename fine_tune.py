# # How to fine-tune chat models
# 
# This notebook provides a step-by-step guide for our new `gpt-3.5-turbo` fine-tuning. We'll perform entity extraction using the [RecipeNLG dataset](https://github.com/Glorf/recipenlg), which provides various recipes and a list of extracted generic ingredients for each. This is a common dataset for named entity recognition (NER) tasks.
# 
# We will go through the following steps:
# 
# 1. **Setup:** Loading our dataset and filtering down to one domain to fine-tune on.
# 2. **Data preparation:** Preparing your data for fine-tuning by creating training and validation examples, and uploading them to the `Files` endpoint.
# 3. **Fine-tuning:** Creating your fine-tuned model.
# 4. **Inference:** Using your fine-tuned model for inference on new inputs.
# 
# By the end of this you should be able to train, evaluate and deploy a fine-tuned `gpt-3.5-turbo` model.
# 
# For more information on fine-tuning, you can refer to our [documentation guide](https://platform.openai.com/docs/guides/fine-tuning), [API reference](https://platform.openai.com/docs/api-reference/fine-tuning) or [blog post](https://openai.com/blog/gpt-3-5-turbo-fine-tuning-and-api-updates)

# ## Setup


# make sure to use the latest version of the openai python package
#!pip install --upgrade openai 


import json
import openai
import os
import pandas as pd
from pprint import pprint
from dotenv import load_dotenv
from auxiliary import save_row
from time import sleep

load_dotenv()
openai.api_key = os.environ.get("OPENAI_API_KEY")
proj_location = os.environ.get("PROJ_LOCATION")
validation = os.environ.get("VALIDATION") == "True"

with open(proj_location + "/proj_details.json", "r") as json_file:
    proj_details = json.load(json_file)

topic = proj_details["TOPIC"]
ScreeningCriteria = proj_details["SCREENING_CRITERIA"]
prompt = proj_details["PROMPT"]
model_to_use = proj_details["SCREENING_MODEL_TO_USE"]

system_message = prompt + " " + str(ScreeningCriteria)

 
# Fine-tuning works best when focused on a particular domain. It's important to make sure your dataset is both focused enough for the model to learn, but general enough that unseen examples won't be missed. Having this in mind, we have extracted a subset from the RecipesNLG dataset to only contain documents from www.cookbooks.com.

# Read in the dataset we'll use for this task.
# This will be the RecipesNLG dataset, which we've cleaned to only contain documents from www.cookbooks.com
df = pd.read_csv(proj_location + "/fine_tune.csv")

df.head()

# ## Data preparation
# 
# We'll begin by preparing our data. When fine-tuning with the `ChatCompletion` format, each training example is a simple list of `messages`. For example, an entry could look like:
# 
# ```
# [{'role': 'system',
#   'content': 'You are a helpful recipe assistant. You are to extract the generic ingredients from each of the recipes provided.'},
# 
#  {'role': 'user',
#   'content': 'Title: No-Bake Nut Cookies\n\nIngredients: ["1 c. firmly packed brown sugar", "1/2 c. evaporated milk", "1/2 tsp. vanilla", "1/2 c. broken nuts (pecans)", "2 Tbsp. butter or margarine", "3 1/2 c. bite size shredded rice biscuits"]\n\nGeneric ingredients: '},
# 
#  {'role': 'assistant',
#   'content': '["brown sugar", "milk", "vanilla", "nuts", "butter", "bite size shredded rice biscuits"]'}]
# ```
# 
# During the training process this conversation will be split, with the final entry being the `completion` that the model will produce, and the remainder of the `messages` acting as the prompt. Consider this when building your training examples - if your model will act on multi-turn conversations, then please provide representative examples so it doesn't perform poorly when the conversation starts to expand.
# 
# Please note that currently there is a 4096 token limit for each training example. Anything longer than this will be truncated at 4096 tokens.
# 


training_data = []


def create_user_message(row):
    return f"""Title: {row['Title']}\n\nAbstract: {row['Abstract']}\n\nAccept?: """

def prepare_example_conversation(row):
    messages = []
    messages.append({"role": "system", "content": system_message})

    user_message = create_user_message(row)
    messages.append({"role": "user", "content": user_message})

    messages.append({"role": "assistant", "content": row["Accept"]})

    return {"messages": messages}

pprint(prepare_example_conversation(df.iloc[0]))

# Let's now do this for a subset of the dataset to use as our training data. You can begin with even 30-50 well-pruned examples. You should see performance continue to scale linearly as you increase the size of the training set, but your jobs will also take longer.


# use the first 100 rows of the dataset for training
if validation:
    training_df = df.loc[0:49]
else:
    training_df = df.loc[0:99]

# apply the prepare_example_conversation function to each row of the training_df
training_data = training_df.apply(prepare_example_conversation, axis=1).tolist()

for example in training_data[:5]:
    print(example)

# In addition to training data, we can also **optionally** provide validation data, which will be used to make sure that the model does not overfit your training set.

if validation:
    validation_df = df.loc[50:99]
    validation_data = validation_df.apply(prepare_example_conversation, axis=1).tolist()

# We then need to save our data as `.jsonl` files, with each line being one training example conversation.
# 


def write_jsonl(data_list: list, filename: str) -> None:
    with open(filename, "w") as out:
        for ddict in data_list:
            jout = json.dumps(ddict) + "\n"
            out.write(jout)


training_file_name = proj_location + "_finetune_training.jsonl"
write_jsonl(training_data, training_file_name)

if validation:
    validation_file_name = proj_location + "_finetune_validation.jsonl"
    write_jsonl(validation_data, validation_file_name)

# This is what the first 5 lines of our training `.jsonl` file look like:


# ### Upload files
# 
# You can now upload the files to our `Files` endpoint to be used by the fine-tuned model.
# 


training_response = openai.File.create(
    file=open(training_file_name, "rb"), purpose="fine-tune"
)
training_file_id = training_response["id"]
print("Training file ID:", training_file_id)

if validation:
    validation_response = openai.File.create(
        file=open(validation_file_name, "rb"), purpose="fine-tune"
    )
    validation_file_id = validation_response["id"]

    print("Validation file ID:", validation_file_id)

# ## Fine-tuning
# 
# Now we can create our fine-tuning job with the generated files and an optional suffix to identify the model. The response will contain an `id` which you can use to retrieve updates on the job.
# 
# Note: The files have to first be processed by our system, so you might get a `File not ready` error. In that case, simply retry a few minutes later.
# 

waiting = True
while waiting:
    try:
        if validation:
            response = openai.FineTuningJob.create(
                training_file=training_file_id,
                validation_file=validation_file_id,
                model="gpt-3.5-turbo",
                suffix="cbfm-screen",
            )
        else:
            response = openai.FineTuningJob.create(
                training_file=training_file_id,
                model="gpt-3.5-turbo",
                suffix="cbfm-screen",
            )


        job_id = response["id"]
        waiting = False
        print("Finished Initialization")
    except:
        print("Model Not Ready yet...")
        sleep(15)

print("Job ID:", response["id"])
print("Status:", response["status"])

# #### Check job status
# 
# You can make a `GET` request to the `https://api.openai.com/v1/alpha/fine-tunes` endpoint to list your alpha fine-tune jobs. In this instance you'll want to check that the ID you got from the previous step ends up as `status: succeeded`.
# 
# Once it is completed, you can use the `result_files` to sample the results from the validation set (if you uploaded one), and use the ID from the `fine_tuned_model` parameter to invoke your trained model.
# 
fine_tuned_model_id = None
while fine_tuned_model_id == None:
    response = openai.FineTuningJob.retrieve(job_id)

    print("Job ID:", response["id"])
    print("Status:", response["status"])
    print("Trained Tokens:", response["trained_tokens"])


    # We can track the progress of the fine-tune with the events endpoint. You can rerun the cell below a few times until the fine-tune is ready.
    # 

    response = openai.FineTuningJob.list_events(id=job_id, limit=50)
    events = response["data"]
    events.reverse()

    for event in events:
        print(event["message"])

    # Now that it's done, we can get a fine-tuned model ID from the job:
    # 

    response = openai.FineTuningJob.retrieve(job_id)
    fine_tuned_model_id = response["fine_tuned_model"]

    print("Fine-tuned model ID:", fine_tuned_model_id)
    print("Waiting for training to finish...")
    sleep(300)

with open("fine_tuned_model.txt", "w") as file:
    file.write(fine_tuned_model_id)
    for event in events:
        file.write(event["message"])

# ## Inference

# The last step is to use your fine-tuned model for inference. Similar to the classic `FineTuning`, you simply call `ChatCompletions` with your new fine-tuned model name filling the `model` parameter.
# 

# ## Conclusion
# 
# Congratulations, you are now ready to fine-tune your own models using the `ChatCompletion` format! We look forward to seeing what you build
# 

