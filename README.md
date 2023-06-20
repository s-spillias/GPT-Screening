
# CI-Review
Code for employing an LLM, *ChatGPT, to screen papers for a systematic review and extract data.

### To Start :

1. Run 'requirements.txt' to install package dependencies. ***I've been using a virtual environment, so you may want to do the same. But might not be necessary.

```
pip install -r requirements.txt
```

2. Create an excel file that includes, at least, Title information and Abstract information. The excel file can be called anything and can be specified in the main script 1_Screening.py '1_pilot.xls'
3. Web of Science* advanced search automatically produces a correctly fomatted excel file. Use this for now. *if using Scopus, you may need to change the title header to 'Title'
4. Place this file in a subdirectory with your preferred project name. Current default is 'CBFM'. 

### Screening :
1. Create / modify the screening criteria in 'set-up.py', found in the project folder.
2. Add your OpenAI key to 'set-up.py'
3. Select the OpenAI model, default is "gpt-3.5-turbo-0301", other models have not been tested.
4. There are a number of settings that can be set in the 'set-up.py' file. 
5. Run the code. May take ~ 10 hours per 1000 articles. Cost for 3.5 Turbo will be ~ 10 USD.
6. New files, one for each agent called '2_*.csv', and a summary file '2a_Screening_summary.csv', will be generated in the project subdirectory 'Output' which will include the results of the screen, the specific responses to each screening criteria, and the LLM's justification.
