import openai
import dotenv
from os import environ

env_file = '../.env'
dotenv.load_dotenv(env_file, override=True)
openai.api_key = environ.get('OPENAI_API_KEY')
ec_uname = environ.get("UNAME")
ec_pass = environ.get("EC_PASS")
ec_url = environ.get("EC_URL")

print(f'url = {ec_url}')
from bs4 import BeautifulSoup as bs 
import requests 
 
payload = { 
	"uname": ec_uname, 
	"pass": ec_pass 
} 
s = requests.session() 
response = s.post(ec_url, data=payload) 
 
from bs4 import BeautifulSoup 
soup = BeautifulSoup(response.content, "html.parser") 

body = soup.body.text
article = (body.split(sep='stories that matter')[1]).split(sep='Word of the day')[0]

def get_response_chat(messages) -> str:
    response = openai.ChatCompletion.create(
        # model=model, temperature=0.0, messages=messages
        model="gpt-3.5-turbo", temperature=0.01, messages=messages
    )
    return response["choices"][0]["message"]["content"] 


system = '''
You are an expert translator. You translate English text to very simple Spanish text that can be understood by a 10 year old. Do not use difficult spanish words.
'''

question = f'''
First separate the English text below into paragraphs. Each paragraph must be related to a particular topic. Then translate each paragraph to simple Spanish that can be understood by a 10 yeard old.
Your response must be in the form of json. do not respond with anything but json format. Also, create a very short title for each of the news paragraphs.

### ENGLISH TEXT:
{article}


### YOU MUST USE THIS JSON TEMPLATE:

{{
    translations:
    [
        {{
        english_version: PARAGRPAH_IN_ENGLISH,
        english_title: TITLE_IN_ENGLISH,
        translated_version: TRANSLATED_PARAGRAPH,
        translated_title: TITLE_IN_ENGLISH
        }},
        ...
    ]
}}

'''

messages = [
    {"role": "system", "content": system},
    {"role": "user", "content": question},
]

translations = get_response_chat(messages=messages)

import json
file_path = "./news.json"
with open(file_path, "w") as json_file:
    json.dump(translations.replace('\n', ''), json_file)


from subprocess import call
import time
import os

# os.chdir(data_path)
call(['pwd'])
call(['git', 'add', '*.json'])
call(['git', 'commit', '-am', 'update' + str(time.time())])
call(['git', 'push', '-f', 'origin', 'master'])