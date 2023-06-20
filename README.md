
# CI-Review
Code for employing an LLM, *ChatGPT, to screen papers for a systematic review and extract data.

This repo is set up to handle multiple projects. To explore data associated with <insert paper link here>, open the CBFM directory.

Otherwise, create a new project folder and follow the steps below.

### To Start :

1. Run 'requirements.txt' to install package dependencies. ***I've been using a virtual environment, so you may want to do the same. But might not be necessary.

```
pip install -r requirements.txt
```

2. Create an excel file that includes, at least, Title information and Abstract information. The excel file can be called anything and can be specified in the main script run.py '1_pilot.xls'
3. At minimum, the file must include columns with the string 'Title' and 'Abstract'
4. Place this file in an 'Input' subdirectory in your project directory; current default is 'CBFM'. 

### Screening :
1. Copy the 'run.py' file into your new project folder.
2. Create / modify the screening criteria in 'run.py', according to your project.
3. Add your OpenAI key to 'run.py'
4. Select the OpenAI model, default is "gpt-3.5-turbo-0301", other models have not been tested.
5. There are a number of settings that can be set in the 'run.py' file. 
6. Run the code. May take ~ 10 hours per 1000 articles. Cost for 3.5 Turbo will be ~ 10 USD.
7. New files, one for each agent called '2_*.csv', and a summary file '2a_Screening_summary.csv', will be generated in the project subdirectory 'Output' which will include the results of the screen, the specific responses to each screening criteria, and the LLM's justification.
