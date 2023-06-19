import requests
from bs4 import BeautifulSoup
import re

from articledownloader.articledownloader import ArticleDownloader





# Define the DOI for the PDF you want to download
doi = all_doi[i]
title = all_title[i]
# Use the DOI to generate a URL to the PDF file
try:
    pdf_url = "https://doi.org/" + doi
except:
    print("No DOI Found")
    next

headers = {'User-Agent': 'Mozilla/5.0'}

# Send a request to the PDF URL and parse the HTML response
response = requests.get(pdf_url)

# Find the link to the PDF file on the page
try:
    response = requests.get(response.url,headers = headers)
    soup = BeautifulSoup(response.content, "html.parser")
    pdf_link = soup.find("meta", {"name":"citation_pdf_url"})["content"]

    # Download the PDF file to your local machine
    if pdf_link:
        pdf_file = requests.get(pdf_link)
        with open(pdf_location + "/" + title[0:9] + ".pdf", "wb") as f:
            f.write(pdf_file.content)
            print("PDF downloaded successfully!")
    else:
        print("No PDF found for DOI " + pdf_url)

except:
    if try_elsevier:
        downloader = ArticleDownloader(els_api_key=elsevier_key)
        my_file = open(pdf_location + "/" + title[0:9] + ".pdf", "wb")  # Need to use 'wb' on Windows
        downloader.get_pdf_from_doi(doi, my_file, 'elsevier')
        my_file.close()
        print("PDF downloaded successfully!")
    else: 
        print("No PDF Found")

