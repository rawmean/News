import openai
import dotenv
from os import environ
import time

env_file = '../.env'
dotenv.load_dotenv(env_file, override=True)
openai.api_key = environ.get('OPENAI_API_KEY')

# Update for BBC News instead of The Economist
print('Switching to BBC News as the source')
from bs4 import BeautifulSoup as bs 
import requests 

def get_response_chat(messages) -> str:
    response = openai.ChatCompletion.create(
        # model=model, temperature=0.0, messages=messages
        model="gpt-4o", temperature=0.01, messages=messages
    )
    return response["choices"][0]["message"]["content"] 


def refresh_news():
    s = requests.session()
    
    # Add proper headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    s.headers.update(headers)
    
    # BBC News World section - no authentication needed
    bbc_url = "https://www.bbc.com/news/world"
    print(f"Accessing BBC News: {bbc_url}")
    
    response = s.get(bbc_url, headers=headers)
    print(f"Response status: {response.status_code}")
    print(f"Content length: {len(response.content)}")
    
    if response.status_code != 200:
        print(f"Error accessing BBC News: {response.status_code}")
        return
    
    soup = bs(response.content, "html.parser")
    
    # BBC News has a different structure - look for article headlines and summaries
    articles = []
    
    # Method 1: Look for main story containers
    story_containers = soup.find_all(['div', 'article'], class_=lambda x: x and ('story' in str(x).lower() or 'promo' in str(x).lower()))
    
    print(f"Found {len(story_containers)} potential story containers")
    
    # Method 2: Look for headline links
    headlines = soup.find_all('a', href=lambda x: x and '/news/' in x)
    
    print(f"Found {len(headlines)} headline links")
    
    # Extract article text from headlines and descriptions
    for i, headline in enumerate(headlines[:10]):  # Limit to first 10 headlines
        title = headline.get_text().strip()
        if len(title) < 10:  # Skip very short titles
            continue
            
        # Look for associated description/summary
        parent = headline.parent
        description = ""
        
        # Try to find description in parent elements
        for _ in range(3):  # Check up to 3 parent levels
            if parent:
                desc_elements = parent.find_all(['p', 'div'], string=lambda text: text and len(text) > 50)
                for desc in desc_elements:
                    desc_text = desc.get_text().strip()
                    if desc_text and desc_text not in title:
                        description = desc_text
                        break
                if description:
                    break
                parent = parent.parent
        
        if title and len(title) > 20:  # Only include substantial titles
            article_text = f"{title}"
            if description:
                article_text += f". {description}"
            articles.append(article_text)
            print(f"Article {len(articles)}: {title[:100]}...")
    
    # Combine all articles into one text
    if not articles:
        print("No articles found, trying alternative extraction...")
        # Alternative: get all paragraph text from the page
        paragraphs = soup.find_all('p')
        all_text = []
        for p in paragraphs:
            text = p.get_text().strip()
            if len(text) > 30 and not any(skip in text.lower() for skip in ['cookie', 'privacy', 'terms', 'advertisement']):
                all_text.append(text)
        
        if all_text:
            # Filter out very short paragraphs and combine
            good_paragraphs = [text for text in all_text if len(text) > 50]
            article = ' '.join(good_paragraphs[:12])  # Take first 12 substantial paragraphs
            print(f"Alternative extraction: {len(article)} characters from {len(good_paragraphs)} paragraphs")
        else:
            print("No content found")
            return
    else:
        article = ' '.join(articles[:8])  # Combine first 8 articles
        print(f"Combined articles: {len(article)} characters")
    
    # Clean up the article
    article = article.replace('"', '`')
    article = article.replace('"', '`')
    
    print(f'========= article preview: {article[:500]}...')

    system_pre = "you are a helpful assistant"
    question_pre  = f'''
    First separate the following english text into paragraphs based on the topic. 
    The output must be in pure json and nothing else. 
    Do not include any paragraph that is about daily quiz.
    Do not include any paragraph that is not news.
    Limit the number of paragraphs to 5. There shall be at most 5 paragraphs.
    Each paragraph must be converted to simple English.

    ### ENGLISH TEXT:
    {article}


    ### YOU MUST USE THIS JSON TEMPLATE:

    #####
    {{
        paragraphs:
            [
                PARAGRPAH_BASED_ON_TOPIC,
                ...
            ]
    }}
    #####
    '''

    messages_pre = [
        {"role": "system", "content": system_pre},
        {"role": "user", "content": question_pre},
    ]

    print('Starting the pre-query')
    paragraphs = get_response_chat(messages=messages_pre)

    print(f'paragraphs: {paragraphs}')


    system = '''
    You are an expert translator. You translate English text to very simple Spanish text that can be understood by a 10 year old. Do not use difficult spanish words.
    '''

    question = f'''
    Then translate each paragraph in the input Paragraphs given below to simple Spanish that can be understood by a 10 year old.
    Your response must be in the form of json. do not respond with anything but json format. Also, create a very short title for each of the news paragraphs.
    Replace all instances of character """ in the values in the json response with character "`""
    Do not use the character """ anywhere in the json response values.

    Do not output ```json. Just give pure json with nothing else 

    ### Input Paragraphs:
    {paragraphs}


    ### YOU MUST USE THIS JSON TEMPLATE:

    #####
    {{
        "translations":
            [
                {{
                    "english_version": PARAGRPAH_IN_ENGLISH,
                    "english_title": TITLE_IN_ENGLISH,
                    "translated_version": TRANSLATED_PARAGRAPH, // do not include any " character here
                    "translated_title": TITLE_IN_ENGLISH
                }},
                ...
            ]
    }}
    #####

    '''

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]

    print('Starting the query ')
    translations = get_response_chat(messages=messages)

    print(translations)
    print(f"translation length = {len(translations)}")

    import json
    file_path = "./news.json"
    with open(file_path, "w") as json_file:
        json.dump(translations.replace('\n', ''), json_file)


    from subprocess import call
    import time
    import os

    # os.chdir(data_path)
    print('uploading to github')
    # call(['pwd'],shell=True)
    call(['git', 'add', '*.json'])
    call(['git', 'commit', '-am', 'update' + str(time.time())])
    call(['git', 'push', '-f', 'origin', 'master'])


if __name__ == '__main__':
    refresh_news()
    while True:
        refresh_news()
        time.sleep(8 * 3600)