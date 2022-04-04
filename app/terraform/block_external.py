from bs4 import BeautifulSoup
import requests

from app import app
from app.models import Proxy


def check_blocks():
    user_agent = {'User-agent': 'BypassCensorship/1.0 (contact@sr2.uk for info)'}
    page = requests.get(app.config['EXTERNAL_CHECK_URL'], headers=user_agent)
    soup = BeautifulSoup(page.content, 'html.parser')
    h2 = soup.find_all('h2')
    div = soup.find_all('div', class_="overflow-auto mb-5")

    results = {}

    i = 0
    while i < len(h2):
        if not div[i].div:
            urls = []
            a = div[i].find_all('a')
            j = 0
            while j < len(a):
                urls.append(a[j].text)
                j += 1
            results[h2[i].text] = urls
        else:
            results[h2[i].text] = []
        i += 1

    for vp in results:
        if vp not in app.config['EXTERNAL_VANTAGE_POINTS']:
            continue
        for url in results[vp]:
            if "cloudfront.net" in url:
                slug = url[len('https://'):][:-len('.cloudfront.net')]
                print(f"Found {slug} blocked")
                proxy = Proxy.query.filter(
                    Proxy.provider == "cloudfront",
                    Proxy.slug == slug
                ).first()
                if not proxy:
                    print("Proxy not found")
                    continue
                if proxy.deprecated:
                    print("Proxy already marked blocked")
                    continue
                proxy.deprecate()
            if "azureedge.net" in url:
                slug = url[len('https://'):][:-len('.azureedge.net')]
                print(f"Found {slug} blocked")
                proxy = Proxy.query.filter(
                    Proxy.provider == "azure_cdn",
                    Proxy.slug == slug
                ).first()
                if not proxy:
                    print("Proxy not found")
                    continue
                if proxy.deprecated:
                    print("Proxy already marked blocked")
                    continue
                proxy.deprecate()


if __name__ == "__main__":
    with app.app_context():
        check_blocks()
