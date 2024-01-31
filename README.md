
# CI-Review
Code for employing an LLM, *ChatGPT, to screen papers for a systematic review and extract data.

This repo is set up to handle multiple projects. To explore data associated with <https://www.researchsquare.com/article/rs-3099291/v1>, open the CBFM directory.

Otherwise, create a new project folder and follow the steps below.

### Search Screen Interactions with ChatGPT:
https://chat.openai.com/share/59350ac4-4906-4b37-bad1-b3d0fc22455c
https://chat.openai.com/share/06f02bc7-c062-4558-a269-0c0954be02d5
https://chat.openai.com/share/d868a1be-2ebe-4fda-bc33-bfcedaeda77e
https://chat.openai.com/share/22bfa6a7-7408-48cd-8a6b-591f96a4fb6b
https://chat.openai.com/share/8d944a52-940c-4cbb-873f-e0f92626b051

### Choosing the best search string
https://chat.openai.com/share/bcf222f4-397c-4f8b-80c8-0c306241170e

### To Start :

1. Run 'requirements.txt' to install package dependencies. ***I've been using a virtual environment, so you may want to do the same. But might not be necessary.

```
pip install -r requirements.txt
```

2. Create an excel file that includes, at least, Title information and Abstract information. The excel file can be called anything and can be specified in the main script run.py '1_pilot.xls'
3. At minimum, the file must include columns with the string 'Title' and 'Abstract'
4. Place this file in an 'Input' subdirectory in your project directory; current default is 'CBFM'. 

### Screening :
1. Copy the .env.example file, and rename it .env. 
2. Create / modify the screening criteria and screening settings, according to your project.
3. Add your OpenAI key to .env
4. Select the OpenAI model
5. Run the code. May take ~ 10 hours per 1000 articles. 

