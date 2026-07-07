import requests

URL = "https://www.walmart.com/search?q=pokeomon+card+"

html = requests.get(URL).text

print(html[:1000])