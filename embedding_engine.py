# Content: Embedding engine to create doc embeddings
# Author: Shuai Guo
# Email: shuaiguo0916@hotmail.com
# Date: August, 2023


from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.embeddings.huggingface import HuggingFaceEmbeddings
from langchain.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.chains.summarize import load_summarize_chain
from langchain.chat_models import ChatOpenAI
from langchain.utilities import ArxivAPIWrapper
import os
import re

from collections import Counter




def remove_headers(text):

    line_frequencies = count_line_frequencies(text)
    
    headers_to_remove = [line for line, count in line_frequencies.items() if count >= 4]

    filtered_headers_to_remove = [header for header in headers_to_remove if header and not header.isnumeric() and len(header.split()) > 1]

    lines = text.split('\n')

    cleaned_lines = [line for line in lines if all(keyword.lower() not in line.lower() for keyword in filtered_headers_to_remove)]

    return '\n'.join(cleaned_lines)



def count_line_frequencies(documents):

    line_counter = Counter()

    for text in documents:

        lines = text.page_content.split('\n')

        line_counter.update(lines)

    return line_counter



def preprocess(text):
    text = text.replace('\n', ' ')
    text = re.sub('\s+', ' ', text)
   # text = text.lower()
    return text

def split_at_references(text):
    # Search for various terms
    matches = list(re.finditer(r'(?<=\n)(References|Bibliography|Work Cited|Works Cited|Source List|Literature Cited|Citation List)', text, re.IGNORECASE))
    
    # If found, use the last occurrence for splitting
    if matches:
        last_match = matches[-1]
        before_references = text[:last_match.start()]
        references = text[last_match.start():]
        return before_references, references
    else:
        return [text]
    
def split_at_references_old(text):
    target_word_pattern = r'a\s*c\s*k\s*n\s*o\s*w\s*l\s*e\s*d\s*g\s*(e\s*m\s*e\s*n\s*t\s|m\s*e\s*n\s*t\s*)'
    match = re.search(target_word_pattern, text, re.I)

    if match:
        index = match.start()
        part1 = text[:index]
        part2 = text[index:]

        parts = [part1,part2]
    else:
        # Handle case where the target words are not found
        parts = [text]
    return parts

def separate_text(documents):
    line_frequencies = count_line_frequencies(documents)

    headers_to_remove = [line for line, count in line_frequencies.items() if count >= 4]

    filtered_headers_to_remove = [header for header in headers_to_remove if header and not header.isnumeric() and len(header.split()) > 1]

    #cleaned_text_by_page = [remove_headers(text, filtered_headers_to_remove) for text in text_chunks]



    # text_list = copy.copy(text_chunks)
    in_frontmatter = True
    in_backmatter = False

    for doc in documents:
       # print(text)
        new_text = preprocess(remove_headers(doc.page_content, filtered_headers_to_remove))
       # new_text = preprocess(doc.page_content)
        if in_backmatter:
            doc.page_content = new_text
            doc.metadata['type'] = 'backmatter'
            continue
        if in_frontmatter:
            abstract_position = new_text.lower().find('abstract')
            if abstract_position != -1:
                split_at_abstract = [new_text[:abstract_position], new_text[abstract_position + len('abstract'):]]
            else:
                split_at_abstract = [new_text]
           #split_at_abstract = new_text.lower().split('abstract')
            if (len(split_at_abstract)>1):
                in_frontmatter = False
                new_text = split_at_abstract[1]
                #text_list.append(Document(page_content= split_at_abstract[0], type= 'frontmatter'))
                doc.page_content = split_at_abstract[0]
                doc.metadata['type'] = 'frontmatter'

        split_at_reference = split_at_references(new_text)
        if (len(split_at_reference)>1):
            in_backmatter = True
            new_text = split_at_reference[0]
       # text_list.append(Document(page_content= text, type= 'main'))
        doc.page_content = new_text
        doc.metadata['type'] = 'main'
    return documents

class Embedder:
    """Embedding engine to create doc embeddings."""

    def __init__(self, engine='OpenAI'):
        """Specify embedding model.

        Args:
        --------------
        engine: the embedding model. 
                For a complete list of supported embedding models in LangChain, 
                see https://python.langchain.com/docs/integrations/text_embedding/
        """
        if engine == 'OpenAI':
            self.embeddings = OpenAIEmbeddings()
        
        elif engine == 'HuggingFace':
            model_name = os.environ.get("EMBEDDING_MODEL")
            model_kwargs = {'device': 'cpu'}
            encode_kwargs = {'normalize_embeddings': False}
            self.embeddings = HuggingFaceEmbeddings(model_name=model_name,
                                model_kwargs=model_kwargs,
                                encode_kwargs=encode_kwargs)
        else:
            raise KeyError("Currently unsupported chat model type!")
        


    def load_n_process_document(self, path):
        """Load and process PDF document.

        Args:
        --------------
        path: path of the paper.
        """

        # Load PDF
        loader = PyMuPDFLoader(path)
        documents = loader.load()

        # Process PDF
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        clean_docs = text_splitter.split_documents(documents)
        text_chunks = separate_text(clean_docs)
        self.documents = [doc for doc in text_chunks if doc.metadata['type'] == 'main']
       # print(self.documents)
        unreadable = self.documents[0]==self.documents[1]
        if unreadable:
            raise ValueError(f'PDF is not Machine-Readable: {path}')



    def create_vectorstore(self, paper):
        """Create vector store for doc Q&A.
           For a complete list of vector stores supported by LangChain,
           see: https://python.langchain.com/docs/integrations/vectorstores/

        Args:
        --------------
        store_path: path of the vector store.

        Outputs:
        --------------
        vectorstore: the created vector store for holding embeddings
        """
        store_path = os.environ.get("PROJ_LOCATION") + "/Embeddings/" + paper
        if not os.path.exists(store_path):
            print("Embeddings not found! Creating new ones")
            self.vectorstore = FAISS.from_documents(self.documents, self.embeddings)
            self.vectorstore.save_local(store_path)

        else:
            print("Embeddings found! Loaded the computed ones")
            self.vectorstore = FAISS.load_local(store_path, self.embeddings)

        return self.vectorstore
    


    def create_summary(self, llm_engine=None, arxiv_id=None):
        """Create paper summary. If it is an arXiv paper, the 
        summary can be directly fetched from the arXiv. Otherwise, 
        the summary will be created by using LangChain's summarize_chain.

        Args:
        --------------
        llm_engine: backbone large language model.
        arxiv_id: id of the arxiv paper.

        Outputs:
        --------------
        summary: the summary of the paper
        """

        if arxiv_id is None:

            if llm_engine is None:
                raise KeyError("Please provide the arXiv id of the paper! \
                               If this is not an arXiv paper, please specify \
                               a LLM engine to perform summarization.")
            
            elif llm_engine == 'OpenAI':
                llm = ChatOpenAI(
                    model_name= os.environ.get("EXTRACTTION_MODEL_TO_USE"),
                    temperature= os.environ.get("TEMPERATURE")
                )

            else:
                raise KeyError("Currently unsupported chat model type!")
            
            chain = load_summarize_chain(llm, chain_type="stuff")
            summary = chain.run(self.documents[:2])

        else:
            
            # Retrieve paper metadata
            arxiv = ArxivAPIWrapper()
            summary = arxiv.run(arxiv_id)

            # String manipulation
            summary = summary.replace('{', '(').replace('}', ')')

        return summary