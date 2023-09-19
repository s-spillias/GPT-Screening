# Content: Class definition of interactive chatbot system 
# Author: Shuai Guo
# Email: shuaiguo0916@hotmail.com
# Date: August, 2023


from langchain.chains import ConversationalRetrievalChain,LLMChain, SequentialChain,ConversationChain, RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.prompts import (
    ChatPromptTemplate, 
    MessagesPlaceholder, 
    SystemMessagePromptTemplate, 
    HumanMessagePromptTemplate
)
from langchain.document_transformers import EmbeddingsRedundantFilter
from langchain.retrievers.document_compressors import DocumentCompressorPipeline
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import EmbeddingsFilter
from langchain import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.retrievers.multi_query import MultiQueryRetriever
import os
from abc import ABC, abstractmethod
from fpdf import FPDF
import random
import string
import auxiliary
from pdf2image import convert_from_path
import pytesseract


def pretty_print_docs(docs):
    return f"".join([f"%%%" + d.page_content for i, d in enumerate(docs)])

def embed_paper(paper_path,embedding):
    pdf_location = os.environ.get("PROJ_LOCATION") + '/' + os.environ.get('PDF_LOCATION')
    try:
        paper_embed = (paper_path.replace(pdf_location + "/","")).replace(".pdf","")
    except:
        print("PDF is not read-able. Attempting OCR...")
        os.system('ocrmypdf "' + paper_path + '" "' + paper_path + '" --force-ocr')
        paper_embed = (paper_path.replace(pdf_location + "/","")).replace(".pdf","")
    embedding.load_n_process_document(paper_path)
    vectorstore = embedding.create_vectorstore(paper=paper_embed)
    return vectorstore

def semantic_search(vectorstore,question,search_type,model_name):
    engine = os.environ.get("EMBEDDING_ENGINE")
    if engine == 'OpenAI':
        llm = OpenAI(
            model_name=model_name,
            temperature=int(os.environ.get("TEMPERATURE"))
        )
        embeddings = OpenAIEmbeddings()
        embeddings_filter = EmbeddingsFilter(embeddings=embeddings, similarity_threshold=0.76)

    else:
        raise KeyError("Currently unsupported chat model type!")

    relevant_docs = RetrievalQA.from_chain_type(llm=llm,
                                                 chain_type="stuff", 
                                                 retriever=vectorstore.as_retriever(search_type=search_type, 
                                                                                    search_kwargs={'score_threshold': 0.8, 
                                                                                                   'fetch_k': 20,
                                                                                                   'k': int(os.environ.get("N_CHUNKS"))}), return_source_documents=True
                                                                                                   )

    return relevant_docs
      
def add_rand_string(question):
    rand_string = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(20))
    new_question = f"Ignore this string: {rand_string}" + "\n\n" + question             
    return new_question

def create_prompt(question,identity,memory,case_study):      
   
    if os.environ.get("RAND_SEED"):
        new_question = add_rand_string(question)
    else:
        new_question = question

    prompt = f""" You are a {identity} and have recently published a scientific paper.  
    Your task is to provide a comprehensive, clear, and accurate answer to questions about your paper for someone interested in {case_study}. You have these memories:
    {memory}..
    When keep the following guidelines in mind:
    - You should answer using similar language as the question.
    - Your responses should only come from the relevant content of this paper, which will be provided to you 
    in the following. 
    - Make sure the Data is correct and don't output false content.
    - Be as concise as possible.
    Tip: If there is no relevant answer to the question based on the context, simply return "NO DATA" and nothing else.
    Question: {new_question}
    """
    
    prompt += """Given the following context, please answer the question.
    
    {context}"""
    
    return prompt


# Helper function for printing docs



def ask_question(paper,question,q_num,vectorstore,identity,memory,search_type,model_name,case_study):
    # Author bot answers
    relevant_docs = semantic_search(vectorstore,question,search_type,model_name)
    result = relevant_docs(create_prompt(question,identity,memory,case_study))
    response = result['result']
   # source = result['source_documents']
  
    compressed_docs = result['source_documents']
    proj_location = os.environ.get("PROJ_LOCATION")
    pdf_location = os.environ.get("PDF_LOCATION") + '/'

    print('\n' + response + '\n')
    # Highlight relevant text in PDF
    context = pretty_print_docs(compressed_docs).split("%%%")
    paper_highlight = paper.replace(pdf_location,'pdf_highlighted/')
  #  auxiliary.highlight_PDF(paper, phrases, paper_highlight,q_num )
 #   page_numbers = [str(src.metadata['page']+1) for src in source]
  #  unique_page_numbers = list(set(page_numbers))
    return response, context


def force_format_ask(author,paper,question,q_num):
    n_attempts = 0
    n_retries = int(os.environ.get("N_RETRIES"))
    while n_attempts < n_retries: # Force a correctly formatted response.
        try:
            response = ask_question(author,paper,question,q_num,identity)
            if '%%' in response:
                data, context = response.split("%%")[:2]
            else:
                data, context = response.split("Context")[:2]
            n_attempts = n_retries + 1
        except:
                print("Bad Parsing...Trying again...")
                n_attempts += 1
    return response, data, context


# Dictionary of prompt types; numbers are the number of chunks sent to LLM


def format_bot(response,format,question):
    llm = OpenAI(model_name=os.environ.get("EXTRACTION_MODEL_TO_USE"), 
                 openai_api_key=os.environ.get("OPENAI_API"), 
                 temperature= int(os.environ.get("TEMPERATURE")))

    data_format = {'Quantitative': 'Return either a single value with any associated units. Or if multiple values are reported, return a list of all possible matching values found in the search results.', 
               'Qualitative': 'Return a comprehensive response of up to three sentences.', 
               'Categorical': 'Return a short phrase or single word only. Be as concise as possible. Do not explain or elaborate.',
               'Theme': 'Return either a single item or a list where each element is at most three words.',
               'Multiple-Choice': 'Return only the applicable choices from the list provided in the Query without elaboration.'}

    format_out = data_format[format]
    print("\n" + format_out + "\n")

   # first step in chain
    template_format = """
        You are a formatting and synthesis algorithm and have been given the following Responses from several scientists about a paper, some of whom have not read the whole paper. 
        Your task is to provide a truthful answer to the question provided based on the Responses from the scientists about their study according to the following Formatting Requirements.
        When answering, re-state the question as the answer and only return text that complies with the formatting requirements. If all responses say "NO DATA", return "NO DATA" only. Do not report any uncertainties.
        Tip: If something is unclear, you don't need to express that.
        Formatting Requirements: {format} 
        Question: {question} 
        Responses: {response} 
        """
    prompt_format = PromptTemplate(

        input_variables=["response","format","question"],

        template=template_format)

    chain_format = LLMChain(llm = llm, prompt = prompt_format, output_key = "formatted_data", verbose = False)

# Combine the first and the second chain

    overall_chain = SequentialChain(chains=[#chain_author,
                                            chain_format                                                                      
                                            ], verbose=False, input_variables = ['response','format',"question"],
                                            output_variables= ["formatted_data"])



    out = overall_chain({"response":response, "format": format_out,"question": question})
    return out


#response = """Data: The unintended consequence of increased water consumption due to 
#the installation of water-efficient showerheads in households was caused by the rebound effect. This effect occurs when water-efficient technologies lead to a decrease in the cost of water use, which in turn leads to an increase in water consumption.%%Context: "The rebound effect occurs when water-efficient technologies lead to a decrease in the cost of water use, which in turn leads to an increase in water consumption. This effect has been observed in a number of studies on water-efficient technologies, including showerheads (Gleick, 2003; Kenway et al., 2008; 
#Lipchin et al., 2011)." (p. 87)%%"""