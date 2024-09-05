import csv
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import uuid
import logging
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def find_sitemap(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    sitemap_url = None
    for link in soup.find_all('a'):
        href = link.get('href', '')
        if 'sitemap' in href:
            sitemap_url = urljoin(url, href)  # Ensure the sitemap URL is absolute
            break
    if sitemap_url is None:
        raise ValueError(f"Sitemap not found for {url}")
    return sitemap_url

def parse_sitemap(sitemap_url, start_date, end_date):
    response = requests.get(sitemap_url)
    soup = BeautifulSoup(response.content, 'xml')  # Use only the 'xml' feature
    articles = []

    for url_tag in soup.find_all('url'):
        loc = url_tag.find('loc').text
        lastmod = url_tag.find('lastmod').text if url_tag.find('lastmod') else None

        if lastmod:
            lastmod_date = datetime.fromisoformat(lastmod.replace('Z', '+00:00'))
            if start_date <= lastmod_date <= end_date:
                articles.append(loc)

    return articles

def scrape_article_data(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    title = soup.title.text if soup.title else ''
    pub_date = datetime.now()
    content_html = str(soup)
    content_text = soup.get_text()
    author = soup.find('meta', attrs={'name': 'author'})
    author = author['content'] if author else ''
    word_count = len(content_text.split())

    article_data = {
        'article_url': url,
        'article_title': title,
        'publishing_date': pub_date,
        'content_html': content_html,
        'content_text': content_text,
        'author': author,
        'word_count': word_count,
        'updated_date': pub_date
    }
    return article_data

def main(input_csv, output_csv, start_date_str, end_date_str):
    start_date = datetime.fromisoformat(start_date_str)
    end_date = datetime.fromisoformat(end_date_str)

    with open(input_csv, 'r') as csvfile:
        reader = csv.reader(csvfile)
        websites = [row for row in reader]

    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'article_id', 'publication_id', 'publication_name', 'publication_url',
            'article_url', 'article_title', 'publishing_year', 'publishing_month',
            'publishing_day', 'publishing_time', 'content_html', 'content_text',
            'author', 'word_count', 'updated_date'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for publication_id, website in enumerate(websites, start=1):
            publication_url = ''
            try:
                # Check if the row has exactly two elements
                if len(website) != 2:
                    logging.warning(f"Skipping invalid row: {website}")
                    continue

                publication_name, publication_url = website
                logging.info(f"Processing {publication_url}")
                sitemap_url = find_sitemap(publication_url)
                articles = parse_sitemap(sitemap_url, start_date, end_date)

                for article_url in articles:
                    article_data = scrape_article_data(article_url)
                    pub_date = article_data['publishing_date']

                    writer.writerow({
                        'article_id': uuid.uuid4(),
                        'publication_id': publication_id,
                        'publication_name': publication_name,
                        'publication_url': publication_url,
                        'article_url': article_data['article_url'],
                        'article_title': article_data['article_title'],
                        'publishing_year': pub_date.year,
                        'publishing_month': pub_date.month,
                        'publishing_day': pub_date.day,
                        'publishing_time': pub_date.strftime('%H:%M:%S'),
                        'content_html': article_data['content_html'],
                        'content_text': article_data['content_text'],
                        'author': article_data['author'],
                        'word_count': article_data['word_count'],
                        'updated_date': article_data['updated_date'].date()
                    })

            except Exception as e:
                logging.error(f"Failed to process {publication_url}: {e}")

if __name__ == '__main__':
    input_csv = 'news_websites.csv'  # Input CSV containing publication names and URLs
    output_csv = input(f"What is the output file name?\n")  # Output CSV to save the articles data
    start_date_str = input(f"What is the start date? YYYY-MM-DD Format.\n")  # Start date in 'YYYY-MM-DD' format
    end_date_str = input(f"What is the end date? YYYY-MM-DD Format.\n")  # End date in 'YYYY-MM-DD' format
    main(input_csv, output_csv, start_date_str, end_date_str)
