
# CI-Review
Code for employing an LLM, *ChatGPT, to screen papers for a systematic review and extract data.

### To Start :

1. Run 'requirements.txt' to install package dependencies. ***I've been using a virtual environment, so you may want to do the same. But might not be necessary.

```
pip install -r requirements.txt
```
2. Create an excel file that includes, at least, Title information and Abstract information. The excel file can be called anything and can be specified in the main script 1_Screening.py '1-pilot.xls'
3. Web of Science* advanced search automatically produces a correctly fomatted excel file. Use this for now. *if using Scopus, you may need to change the title header to 'Title'
4. Place this file in a subdirectory with your preferred project name. Current default is 'Test'. 

### Screening :
1. Create / modify the screening criteria in 'set-up.py'
2. Add your OpenAI key, if you have one. Otherwise, mine is included here while this repo is private.
3. Select the OpenAI model, default is "gpt-3.5-turbo-0301", which is apparently cheap and optimized for chat.
4. Run the code. May take ~ 10 hours per 1000 articles. Cost for 3.5 Turbo will be ~ 10 USD.
5. A new file, '2_Screening.csv', will be generated in the project subdirectory which will include the results of the screen, the specific responses to each screening criteria, and the LLM's justification.

### Obtain PDFs:
1. Surprisingly, this was HARD to do automatically. All of the packages I tried failed to download, I think maybe because of the CSIRO firewall?
2. There is a script in '2_GetMetaData.py' which will get most non-elsevier papers. This will run if 'get_pdfs' is set to 'True'
3. Another approach is to run 2_GetMetaData.py with the default (get_pdfs set to False), which will generate a bibtex file, '2a_all_bib.txt' for each of the included studies in '2_Screening.csv'
4. This bibtex file can then be imported to Zotero, Mendeley, or Endnote, and then you can use the automatic PDF download functionality of those programs. (keen to hear thoughts on if this is possible to do programmatically).
5. Once all of the PDFs are obtained, move them to the project folder. It's fine if they are in subfolders, as for example Zotero does (these are the folders with random character string names).

### Coding / Extracting Data from Full-Text PDFs
1. Built on the functionality found at this github repo: https://github.com/bhaskatripathi/pdfGPT. See the README there for details.
2. In the script, 3_CodePDFs.py, set the directory where the PDFs are located, the OpenAIkey and the choice of model.
3. Write out your desired data queries in the 'all_questions' variable.
4. For each question, describe the type of data desired in the 'prompt_type' variable. (i.e. quantitative, qualitative, categorical, etc.)
5. Then for each of these data types, describe, in detail, the format that the response should take. The more specific the more likely your request will be followed by the LLM.
6. You may edit the Base Prompt, if necessary. 
7. Running the file will initiate the coding process, and will output a file, '3_codings.xlsx', in the working folder, which will include two sheets, one for the Data requested, and the other for the specific context from which the data was drawn.
