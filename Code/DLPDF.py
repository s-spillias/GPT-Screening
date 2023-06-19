# Import libraries
import requests
from bs4 import BeautifulSoup
 
url = 'https://doi.org/10.1038/s41467-022-29818-z'

headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get(url, headers = headers)
new_url = r.url
r_new = requests.get(new_url, headers = headers)
 
# Parse text obtained
soup = BeautifulSoup(r_new.text, 'html.parser')
 
# Find all hyperlinks present on webpage
links = soup.find_all('a')

i = 0
 
links_pdf = []
# From all links check for pdf link and
# if present download file
for link in links:
    if ('.pdf' in link.get('href', [])
        ):
        links_pdf.append(link)
        i += 1
        print("Downloading file: ", i)
        print(link)
        # Get response object for link
        response = requests.get(link.get('href'), headers)
 
        # Write content in pdf file
        pdf = open("pdf"+str(i)+".pdf", 'wb')
        pdf.write(response.content)
        pdf.close()
        print("File ", i, " downloaded")
 
print("All PDF files downloaded")

