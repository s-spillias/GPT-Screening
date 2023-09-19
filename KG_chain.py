from langchain.chains import LLMChain, SequentialChain
from langchain.prompts import PromptTemplate
from langchain import OpenAI
from langchain.memory import SimpleMemory

import csv
import os
import string
import pandas as pd
import json

def KG_chain(input_text, csv_file_name,entities_in):
    API_KEY = "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"
    llm = OpenAI(model_name="gpt-3.5-turbo-0301", openai_api_key=API_KEY, temperature= 0)

    # Reduce article size
    template_reduce= "Reduce the size of the following text by removing extraneous information and focusing on the main points. Text: {text}"

    reduce_prompt = PromptTemplate(

        input_variables=["text"],

        template=template_reduce)

    reduce_chain = LLMChain(llm = llm, prompt = reduce_prompt, output_key = "text", verbose = False)

    # first step in chain
    template_entity = "Identify the relevant distinct entities/concepts from the following text. Only return the names of the entities without description. Use a minimum number of words to name each entity. Be concise. Do not group distinct concepts with 'and', instead return separate entity names. If an entity is alread listed below, use that name. Return the list of entities provided augmented by the new entities you have found. Tip: Ignore information in parentheses, but pay close attention to proper names outside of parentheses. Text: {text}. \n\n Entities: {entities}"

    entity_prompt = PromptTemplate(

        input_variables=["text",'entities'],

        template=template_entity)

    entity_chain = LLMChain(llm = llm, prompt = entity_prompt, output_key = "list1", verbose = False)

    # second step in chain
    template_consolidate = "Revise the following list by re-naming entities that refer to the same things from the Text. Do not simply eliminate entries in the list, merely re-group similar entities under a common label. For example, 'water samples' and 'samples' can both be referred to as 'samples'. Do not group distinct concepts with 'and', instead return separate entity names. Text: {text} \n List: {list1}"

    consolidate_prompt = PromptTemplate(

        input_variables=["list1","text"],

        template=template_consolidate)

    consolidate_chain = LLMChain(llm=llm, prompt=consolidate_prompt,output_key = "list2", verbose = False)

    # Convert to tuples with relationships

    template_tuple = "Using just the entities from the list below as 'source' and 'target'; use the original article text to infer as many relationships as you can and generate tuples like (source, relation, target). Make sure there are always a source, relation and target in the tuple. \nExample:\noriginal article text: John knows React, Golang, and Python. John is good at Software Engineering and Leadership\ntuple: \n(John, knows, React); (John, knows, Golang); (John, knows, Python); (John, good at, Software Engineering); (John, good at, Leadership);\n original article text: Bob is Alice's father. Alice has one brother John. \n tuple: \n(Bob, father of, Alice); (John, brother of, Alice). \n\nList: {list2}\n\n Original Article Text: {text} \n\n Tuple:"


    tuple_prompt = PromptTemplate(

        input_variables=["list2","text"],

        template=template_tuple)

    tuple_chain = LLMChain(llm=llm, prompt=tuple_prompt,output_key = "tuples1", verbose = False)



    # Reflection chain
    template_reflection = "Compare the set of tuples with the text and, if necessary, revise the list of tuples to incorporate any tuples that might be missing. Ensure that each tuple has exactly three elements. Return the comprehensive list of tuples. Text: {text} \n List: {tuples1}"
    
    reflection_prompt = PromptTemplate(

        input_variables=["tuples1","text"],

        template=template_reflection,)

    reflection_chain = LLMChain(llm = llm, prompt= reflection_prompt, output_key = "tuples2", verbose = False)

    # Combine the first and the second chain

    overall_chain = SequentialChain(chains=[#reduce_chain,
                                            entity_chain,
                                            consolidate_chain,
                                            tuple_chain,
                                           # reflection_chain,
                                            ], verbose=True, input_variables = ['text','entities'],
                                            #memory=SimpleMemory(memories={"entities": entities_in} ),
                                            output_variables= ['tuples1','list2'])


    out = overall_chain({"text":input_text, "entities": entities_in})



    # Split the input by semicolon to separate tuples
    tuple_strings = out['tuples1'].split(";")

    # Process each tuple string
    translator = str.maketrans("", "", string.punctuation.replace(" ", ""))  # Translation table for punctuation removal
    tuples_list_lower = []
    for tuple_str in tuple_strings:
        # Split each tuple string by comma and strip unnecessary characters
        parts = [item.strip(" ()") for item in tuple_str.split(",")]
        
        # Create a new tuple with lowercase and punctuation removed for each part
        new_tuple = tuple(item.lower().translate(translator) for item in parts)
        
        # Append the new tuple to the list
        tuples_list_lower.append(new_tuple)

        # Specify the CSV file name
   

    # Check if the CSV file exists
    file_exists = os.path.exists(csv_file_name)

    # Open the CSV file in append mode
    with open(csv_file_name, 'a', newline='', encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file)

        # Write the header row only if the file doesn't exist
        if not file_exists:
            csv_writer.writerow(["Source","Relationship", "Target"])

        # Write the data rows
        csv_writer.writerows(tuples_list_lower)
    return out

def KG_save(csv_file_name,json_file_name):
        # Read existing CSV file if it exists
    tuples_list_lower = []
    if os.path.exists(csv_file_name):
        with open(csv_file_name, 'r', newline='', encoding='utf-8') as csv_file:
            csv_reader = csv.reader(csv_file)
            next(csv_reader)  # Skip header row
            for row in csv_reader:
                if len(row) == 3:
                   # print("cleaned")
                    tuples_list_lower.append(tuple(item.lower() for item in row))
                else:
                    continue

    # Create a DataFrame from the list of tuples
    df = pd.DataFrame(tuples_list_lower, columns=["source", "relation", "target"])

    # Drop duplicates and keep the first occurrence
    df_deduplicated = df.drop_duplicates()

    # Convert the DataFrame back to a list of tuples
    tuples_list_lower_deduplicated = [tuple(row) for row in df_deduplicated.to_numpy()]

    # Create a list of dictionaries for each tuple
    result = []
    for tup in tuples_list_lower_deduplicated:
            source, relation, target = tup
            source = source.replace(" ", "_")
            relation = relation.replace(" ", "_")
            target = target.replace(" ", "_")
            result.append({"source": source, "relation": relation, "target": target})


    # Convert the list of dictionaries to a JSON object
    json_object = json.dumps(result, ensure_ascii=False)

    # Print the JSON object
    print(json_object)

    # Write the JSON object to a file
    with open(json_file_name, 'w', encoding='utf-8') as json_file:
        json_file.write(json_object)

def extract_unique_values(input_str):
    # Split the input into individual tuples based on semicolons
    tuple_strs = [string.title() for string in input_str.strip('().').split('; ')]

    # Initialize an empty set to store unique values
    unique_values = set()

    # Iterate through each tuple string
    for tuple_str in tuple_strs:
        # Split the tuple into its components
        parts = tuple_str.split(', ')
        
        # Ensure that only the first and third values are added to the set
        if len(parts) >= 3:
            first_value = parts[0].replace("(", "").replace(")", "")
            third_value = parts[2].replace("(", "").replace(")", "")
            unique_values.add(first_value)
            unique_values.add(third_value)

    # Convert the set back to a list if needed
    result_list = list(unique_values)

    #result_list = [s.replace("(", "").replace(")", "") for s in result_list]

    return result_list