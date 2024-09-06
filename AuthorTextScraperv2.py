import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import re
import json
from datetime import datetime, timedelta


def get_author(soup_object):
    # Check for <p><strong>By Author Name</strong></p> first
    by_p_tag = soup_object.find('p')
    if by_p_tag and by_p_tag.find('strong') and by_p_tag.find('strong').text.startswith('By '):
        author_name = by_p_tag.find('strong').text[len('By '):]
        return author_name.strip()

    # Check for meta tags
    meta_tags = [
        soup_object.find('meta', attrs={'name': 'sailthru.author'}),
        soup_object.find('meta', attrs={'name': 'author'}),
        soup_object.find('meta', attrs={'name': 'article:author'}),
        soup_object.find('meta', attrs={'property': 'article:author'})
    ]

    for meta_tag in meta_tags:
        if meta_tag and 'content' in meta_tag.attrs:
            content = meta_tag['content']
            if content.startswith("https://"):
                # Extract the name from the URL
                match = re.search(r'/([^/]+)/?$', content)
                if match:
                    return match.group(1).replace('-', ' ').title()
            elif content.startswith("@"):
                # Handle social media handle or identifier
                return content[1:].replace('-', ' ').title()
            else:
                return content

    # Fallback to checking within the author-description div
    author_div = soup_object.find('div', class_='author-description')
    if author_div:
        author_tag = author_div.find('h5').find('a', itemprop='author')
        if author_tag:
            return author_tag.get_text()

    # Check for <a> tags with itemprop="author"
    author_a_tag = soup_object.find('a', itemprop='author')
    if author_a_tag:
        return author_a_tag.get_text()

    # Check for <script type="application/ld+json"> for author data
    script_tag = soup_object.find('script', type='application/ld+json')
    if script_tag:
        try:
            json_data = json.loads(script_tag.string)
            if 'author' in json_data:
                author_name = json_data['author'].get('name')
                if author_name:
                    return author_name
        except json.JSONDecodeError:
            pass

    # Check for <span> with class 'meta_text' followed by an <a> tag
    meta_text_span = soup_object.find('span', class_='meta_text')
    if meta_text_span and meta_text_span.next_sibling and meta_text_span.next_sibling.name == 'a':
        return meta_text_span.next_sibling.get_text()

    # Check for author name in the author-box div
    author_box_div = soup_object.find('div', class_='author-box')
    if author_box_div:
        author_name = author_box_div.find('h3')
        if author_name:
            return author_name.get_text()

    # Check for <span> followed by an <a> tag with class 'PostByline_author__5KK7G'
    by_span = soup_object.find('span', text="By ")
    if by_span and by_span.find_next_sibling('span'):
        author_a_tag = by_span.find_next_sibling('span').find('a', class_='PostByline_author__5KK7G')
        if author_a_tag:
            return author_a_tag.get_text()

    # Check for author in body class
    body_tag = soup_object.find('body')
    if body_tag and 'class' in body_tag.attrs:
        body_classes = body_tag['class']
        for cls in body_classes:
            if cls.startswith('author-'):
                return cls[len('author-'):].replace('-', ' ').title()

    return "none"


# Define paths
input_path = os.path.join(os.path.expanduser("~"), "Desktop")
output_path = os.path.join(os.path.expanduser("~"), "Desktop")

# Create output directory if it doesn't exist
if not os.path.exists(output_path):
    os.makedirs(output_path)

# Get the date range for the last month
today = datetime.now()
last_month = today - timedelta(days=30)

# Iterate through each file in the input path
for filename in os.listdir(input_path):
    if not filename.endswith('.csv'):
        print("Invalid file!")
        continue
    file_path = os.path.join(input_path, filename)
    if os.path.isfile(file_path):
        df = pd.read_csv(file_path)

        # Ensure 'date' column is in datetime format and naive
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.tz_localize(None)

        # Ensure last_month is naive
        last_month = last_month.replace(tzinfo=None)

        # Filter rows for the last month
        df_filtered = df[df['date'] >= last_month]

        articles = df_filtered['url'].tolist()
        authors = []
        for url in articles:
            print(f"Getting data from {url}")
            headers = {'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:128.0) Gecko/20100101 Firefox/128.0"}
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                content = response.text
            else:
                print(f"Failed to fetch article from {url}")
                authors.append("none")
                continue

            soup = BeautifulSoup(content, 'html.parser')
            author = get_author(soup)
            print(f"Author: {author}")
            authors.append(author)

        df_filtered['author'] = authors

        # Save the filtered DataFrame to the output directory
        output_file_path = os.path.join(output_path, filename)
        df_filtered.to_csv(output_file_path, index=False)

print("Process completed.")
exit(0)
