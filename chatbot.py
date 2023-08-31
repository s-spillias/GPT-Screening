# Content: Class definition of interactive chatbot system 
# Author: Shuai Guo
# Email: shuaiguo0916@hotmail.com
# Date: August, 2023


from langchain.chains import ConversationalRetrievalChain,LLMChain, SequentialChain,ConversationChain
from langchain.prompts import PromptTemplate
from langchain.prompts import (
    ChatPromptTemplate, 
    MessagesPlaceholder, 
    SystemMessagePromptTemplate, 
    HumanMessagePromptTemplate
)
from langchain import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
import os
from abc import ABC, abstractmethod
from fpdf import FPDF
import random
import string
import auxiliary



class Chatbot(ABC):
    """Class definition for a single chatbot with memory, created with LangChain."""
    
    
    def __init__(self, engine):
        """Initialize the large language model and its associated memory.
        The memory can be an LangChain emory object, or a list of chat history.

        Args:
        --------------
        engine: the backbone llm-based chat model.
                "OpenAI" stands for OpenAI chat model;
                Other chat models are also possible in LangChain, 
                see https://python.langchain.com/en/latest/modules/models/chat/integrations.html
        """
        
        # Instantiate llm
        if engine == 'OpenAI':
            self.llm = ChatOpenAI(
                model_name=os.environ.get("EXTRACTION_MODEL_TO_USE"),
                temperature=os.environ.get("TEMPERATURE")
            )

        else:
            raise KeyError("Currently unsupported chat model type!")


    @abstractmethod
    def instruct(self):
        """Determine the context of chatbot interaction. 
        """
        pass


    @abstractmethod
    def step(self):
        """Action produced by the chatbot. 
        """
        pass
        

    @abstractmethod
    def _specify_system_message(self):
        """Prompt engineering for chatbot.
        """       
        pass
    



class ReviewerBot(Chatbot):
    """Class definition for the reviewer bot, created with LangChain."""
    
    def __init__(self, engine):
        """Setup reviewer bot.
        
        Args:
        --------------
        engine: the backbone llm-based chat model.
                "OpenAI" stands for OpenAI chat model;
                Other chat models are also possible in LangChain, 
                see https://python.langchain.com/en/latest/modules/models/chat/integrations.html
        """
        
        # Instantiate llm
        super().__init__(engine)
        
        # Instantiate memory
        self.memory = ConversationBufferMemory(return_messages=True)


    def instruct(self, topic, format):
        """Determine the context of reviewer chatbot. 
        
        Args:
        ------
        topic: the topic of the paper
        abstract: the abstract of the paper
        """
        self.topic = topic
        self.format = format
        
        # Define prompt template
        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(self._specify_system_message())#,
          #  MessagesPlaceholder(variable_name="history"),
          #  HumanMessagePromptTemplate.from_template("""{input}""")
        ])
        
        # Create conversation chain
        self.conversation = ConversationChain(memory=self.memory, prompt=prompt, 
                                              llm=self.llm, verbose=False)
        

    def step(self, prompt):
        """reviewer chatbot asks question. 
        
        Args:
        ------
        prompt: Previous answer provided by the author bot.
        """
        response = self.conversation.predict(input=prompt)
        
        return response
        


    def _specify_system_message(self):
        """Specify the behavior of the reviewer chatbot.


        Outputs:
        --------
        prompt: instructions for the chatbot.
        """       
        
        # Compile bot instructions 
        prompt = f"""You are a technical reviewer interested in {self.topic}, 
        Your task is to distill a recently published scientific paper on this topic through
        an interview with the author, which is played by another chatbot.
        Your objective is to re-format the responses of the other chatbot to comply with the Formatting Requirements provided.
        If the author has said that the information is not available, reply with 'No Data'. 
        Formatting Requirements: {self.format}
        """
        prompt += """Given the following context, please answer the question.
        
        {history}"""
            
        return prompt



class AuthorBot(Chatbot):
    """Class definition for the author bot, created with LangChain."""
    
    def __init__(self, engine, vectorstore, debug=False):
        """Select backbone large language model, as well as instantiate 
        the memory for creating language chain in LangChain.
        
        Args:
        --------------
        engine: the backbone llm-based chat model.
        vectorstore: embedding vectors of the paper.
        """
        
        # Instantiate llm
        super().__init__(engine)
        
        # Instantiate memory
        self.chat_history = []
        
        # Instantiate embedding index
        self.vectorstore = vectorstore

        self.debug = debug
        
        
        
    def instruct(self, topic):
        """Determine the context of author chatbot. 
        
        Args:
        -------
        topic: the topic of the paper.
        """

        # Specify topic
        self.topic = topic
        
        # Define prompt template
        qa_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(self._specify_system_message()),
            HumanMessagePromptTemplate.from_template("{question}")
        ])
        
        # Create conversation chain
        self.conversation_qa = ConversationalRetrievalChain.from_llm(llm=self.llm, verbose=self.debug,
                                                                     retriever=self.vectorstore.as_retriever(
                                                                         search_kwargs={"k": 3}),
                                                                    chain_type="stuff", return_source_documents=True,
                                                                    combine_docs_chain_kwargs={'prompt': qa_prompt})

        
        
    def step(self, prompt):
        """Author chatbot answers question. 
        
        Args:
        ------
        prompt: question raised by reviewer bot.

        Outputs:
        ------
        answer: the author bot's answer
        source_documents: documents that author bot used to answer questions
        """
        response = self.conversation_qa({"question": prompt, "chat_history": self.chat_history})
       # self.chat_history.append((prompt, response["answer"]))
        
        return response["answer"], response["source_documents"]
        
        
        
    def _specify_system_message(self):
        """Specify the behavior of the author chatbot.


        Outputs:
        --------
        prompt: instructions for the chatbot.
        """       
        
        # Compile bot instructions 
        prompt = f"""You are the author of a recently published scientific paper on {self.topic}.
        You are being interviewed by a scientist reviewing your work who is played by another chatbot and
        looking to write an article that synthesises your work.
        Your task is to provide comprehensive, clear, and accurate answers to the scientist's questions.
        Please keep the following guidelines in mind:
        - Try to explain complex concepts and technical terms in an understandable way, without sacrificing accuracy.
        - Your responses should only come from the relevant content of this paper, which will be provided to you 
        in the following. 
        - Compose your answer strictly in two parts, 'Data' and 'Context', according to the format between **** below. 
        Separate 'Data' and 'Context' using this symbol %% and ensure that the words 'Data' and 'Context' are present.
        **** Data: Answer to the query according to the Data Format. %% Context: 
        'specific quotation from the study to support the Data above'. ****
        For each point in your Data, provide a specific quotation from the study for context.
        - Make sure the Data is correct and don't output false content.
        """
        
        prompt += """Given the following context, please answer the question.
        
        {context}"""
        
        return prompt

def embed_paper(paper_path,embedding):
    pdf_location = os.environ.get("PROJ_LOCATION") + '/' + os.environ.get('PDF_LOCATION')
    paper = (paper_path.replace(pdf_location + "/","")).replace(".pdf","")
    embedding.load_n_process_document(paper_path)
    vectorstore = embedding.create_vectorstore(paper=paper)
    author = AuthorBot('OpenAI', vectorstore)
    topic=os.environ.get("TOPIC")
    print(topic)
    author.instruct(topic)
    return author

def add_rand_string(question):
    rand_string = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(20))
    new_question = f"Ignore this string: {rand_string}" + "\n\n" + question             
    return new_question

def ask_question(author,paper,question,q_num):
    # Author bot answers
    proj_location = os.environ.get("PROJ_LOCATION")
    pdf_location = os.environ.get("PDF_LOCATION") + '/'
    if os.environ.get("RAND_SEED"):
        question = add_rand_string(question)
    response, source = author.step(question)
    print('\n' + response + '\n')
    # Highlight relevant text in PDF
    phrases = [src.page_content for src in source]
    paper_highlight = paper.replace(pdf_location,'pdf_highlighted/')
    auxiliary.highlight_PDF(paper, phrases, paper_highlight,q_num )
 #   page_numbers = [str(src.metadata['page']+1) for src in source]
  #  unique_page_numbers = list(set(page_numbers))
    return response


def force_format_ask(author,paper,question,q_num):
    n_attempts = 0
    n_retries = int(os.environ.get("N_RETRIES"))
    while n_attempts < n_retries: # Force a correctly formatted response.
        try:
            response = ask_question(author,paper,question,q_num)
            if '%%' in response:
                data, context = response.split("%%")
            else:
                data, context = response.split("Context")
            n_attempts = n_retries + 1
        except:
                print("Bad Parsing...Trying again...")
                n_attempts += 1
    return response, data, context


# Dictionary of prompt types; numbers are the number of chunks sent to LLM


def format_bot(response,topic,format):
    llm = OpenAI(model_name=os.environ.get("EXTRACTION_MODEL_TO_USE"), 
                 openai_api_key=os.environ.get("OPENAI_API"), 
                 temperature= int(os.environ.get("TEMPERATURE")))

    data_format = {'Quantitative': 'Return either a single value with any associated units. Or if multiple values are reported, return a list of all possible matching values found in the search results.', 
               'Qualitative': 'Return a comprehensive response of up to three sentences.', 
               'Categorical': 'Return a short phrase or single word only. Be as concise as possible. Do not explain or elaborate.',
               'Theme': 'Return either a single item or a list where each element is at most three words. For each element, provide one or two examples from the study in a citation list after.',
               'Multiple-Choice': 'Return only the applicable choices from the list provided in the Query without elaboration. Provide a quote from the study that justifies this choice in a citation after.'}

    format_out = data_format[format]
    print("\n" + format_out + "\n")

   # first step in chain
    template_format = """
        You are a technical reviewer interested in {topic} and have been given the following Response from a scientist about their paper. 
        Your task is to summarise content of the scientist's response about their study according to the following Formatting Requirements.
        Your objective is to extract the content of the scientist to comply with the Formatting Requirements provided so that it can be input in a database.
        In providing your answer, only return text that complies with the formatting requirements. Do not provide extraneous signifiers such as "Data:", "Response:", etc.
        Formatting Requirements: {format}
        Response: {response}
        """
    prompt_format = PromptTemplate(

        input_variables=["topic","response","format"],

        template=template_format)

    chain_format = LLMChain(llm = llm, prompt = prompt_format, output_key = "formatted_data", verbose = False)

# Combine the first and the second chain

    overall_chain = SequentialChain(chains=[#chain_author,
                                            chain_format                                                                      
                                            ], verbose=False, input_variables = ['response','topic','format'],
                                            output_variables= ["formatted_data"])



    out = overall_chain({"response":response, "topic": topic,"format": format_out })
    return out