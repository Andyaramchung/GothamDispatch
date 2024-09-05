import requests
from lxml import etree
import pandas as pd
import xml.etree.ElementTree as eT
import os


# Load the sitemap URLs and associated metadata from a CSV file
sitemapsFrame = pd.read_csv("news_websites.csv")
sitemaps = sitemapsFrame["sitemap_url"].tolist()


def get_sitemap_url(xml_content):
    try:
        # Parse the XML content
        new_root = eT.fromstring(xml_content)

        # Define the namespace map
        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

        # Find the <loc> tag using the namespace
        loc_tag = new_root.find('.//ns:loc', namespaces=ns)
        if loc_tag is not None and loc_tag.text:
            return loc_tag.text.strip()
        else:
            return None
    except eT.ParseError as exception:
        print(f"XML Parsing Error: {exception}")
        return None


# Iterate over each sitemap URL to fetch and parse data
for sitemap_url in sitemaps:
    print(f"Getting data from {sitemap_url}")
    headers = {'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:128.0) Gecko/20100101 Firefox/128.0"}
    response = requests.get(sitemap_url, headers=headers)

    if response.status_code == 200:
        sitemap_content = response.text
    else:
        print(f"Failed to fetch sitemap from {sitemap_url}")
        continue

    if sitemap_url == "https://www.westsidespirit.com/sitemapforgoogle.xml":
        sitemap_url = get_sitemap_url(sitemap_content)
        response = requests.get(sitemap_url, headers=headers)
        sitemap_content = response.text
        sitemap_url = "https://www.westsidespirit.com/sitemapforgoogle.xml"

    if sitemap_url == "https://www.chelseanewsny.com/sitemapforgoogle.xml":
        sitemap_url = get_sitemap_url(sitemap_content)
        response = requests.get(sitemap_url, headers=headers)
        sitemap_content = response.text
        sitemap_url = "https://www.chelseanewsny.com/sitemapforgoogle.xml"

    try:
        root = etree.fromstring(sitemap_content.encode())
    except etree.XMLSyntaxError as e:
        print(f"XML Syntax Error: {e}")
        continue

    # Get metadata from the CSV file for the current sitemap URL
    metadata = sitemapsFrame[sitemapsFrame['sitemap_url'] == sitemap_url].iloc[0]
    publicationName = metadata['publication_name']
    publicationURL = metadata['url']
    boroughName = metadata['borough']
    neighborhoodName = metadata['neighborhood']
    frequencyTime = metadata['frequency']

    # Namespace map for parsing XML with namespaces
    nsmap = {'ns': root.nsmap.get(None)} if None in root.nsmap else {}
    print(f"Namespaces: {nsmap}")

    # Find all url elements using the namespace map if necessary
    url_elements = root.findall('.//ns:url', namespaces=nsmap) if nsmap else root.findall('.//url')
    print(f"Found {len(url_elements)} url elements")

    # Initialize lists to store the extracted data
    dates, urls, publication_name, publication_url, borough, neighborhood, frequency = ([] for _ in range(7))

    for url_elem in url_elements:
        # Extract the loc element (URL)
        loc_elem = url_elem.find('ns:loc', namespaces=nsmap) if nsmap else url_elem.find('loc')
        if loc_elem is not None:
            urls.append(loc_elem.text)
            publication_name.append(publicationName)
            publication_url.append(publicationURL)
            borough.append(boroughName)
            neighborhood.append(neighborhoodName)
            frequency.append(frequencyTime)

        # Extract the lastmod element (date)
        lastmod_elem = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')
        if lastmod_elem is not None:
            dates.append(lastmod_elem.text)
        else:
            lastmod_elem = url_elem.find('{http://www.google.com/schemas/sitemap-news/0.9}publication_date')
            if lastmod_elem is not None:
                dates.append(lastmod_elem.text)
            else:
                lastmod_elem = url_elem.find(
                    '{http://www.google.com/schemas/sitemap-news/0.9}news/'
                    '{http://www.google.com/schemas/sitemap-news/0.9}publication_date')
                if lastmod_elem is not None:
                    dates.append(lastmod_elem.text)
                else:
                    dates.append(None)

    # Create a DataFrame from the extracted data
    df = pd.DataFrame({
        "publication name": publication_name,
        "publication url": publication_url,
        "url": urls,
        "date": dates,
        "borough": borough,
        "neighborhood": neighborhood,
        "frequency": frequency
    })

    # Definition of a function that fixes non-standard dates to fit the datetime requirements
    def gothamist_date_fix(data):
        dates_list = data["date"].tolist()

        new_dates = []

        for date in dates_list:
            date = date.replace('T', ' ')
            date = date[:-13]
            date = date + "+00:00"
            new_dates.append(date)

        data["date"] = new_dates
        return data

    # Definition of a function that fixes non-standard dates to fit the datetime requirements
    def bklyn_date_fix(data):
        dates_list = data["date"].tolist()

        new_dates = []

        for date in dates_list:
            date = date.replace('T', ' ')
            date = date[:-6]
            date = date + "+00:00"
            new_dates.append(date)

        data["date"] = new_dates
        return data

    if publicationName == "Gothamist":
        df = gothamist_date_fix(df)
    if publicationName == "Brooklyn  Buzz":
        df = bklyn_date_fix(df)
    if publicationName == "The Spirit":
        df = bklyn_date_fix(df)

    df["date"] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    df['day'] = df['date'].dt.day

    # Ensure the target directory exists
    path = os.path.join(os.path.expanduser("~"), "Documents", "24-25", "SIPA + Wayback", "GothamDispatch", "docs")
    os.makedirs(path, exist_ok=True)

    # Save the DataFrame to a CSV file
    filepath = os.path.join(path, f"{publicationName}.csv")
    df.to_csv(filepath, index=False)

exit(0)
