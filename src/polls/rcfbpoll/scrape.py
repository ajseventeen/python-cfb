import os
import re
import csv
from tqdm import tqdm
from bs4 import BeautifulSoup
import urllib
import requests
from polls.analysis import Voter


def get_page_of_type_for_poll(page_type, poll_id, params):
    url = f'https://poll.redditcfb.com/poll/{page_type}/{poll_id}/'
    if page_type == 'ballots':
        url += '1'

    response = requests.get(url, params=urllib.parse.urlencode(params, quote_via=urllib.parse.quote))
    soup = BeautifulSoup(response.text, features='html.parser')
    return soup


def get_ballot_page_for_poll(poll_id, page_number):
    return get_page_of_type_for_poll('ballots', poll_id, {
        'page': page_number
        })


def get_poll_id(year, week):
    url = f'https://poll.redditcfb.com/poll/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, features='html.parser')
    table = soup.find('h3', text=year).find_next_sibling()
    link = table.find('a', text='Preseason' if week == 1 else f'Week {week}')
    return link['href'].split('/')[-2]


def is_last_page(page, page_number):
    next_button = page.find('a', string='Next')
    return next_button is None


def scrape_ballots_for_poll(year, week, **kwargs):
    return scrape_ballots_for_poll_by_id(get_poll_id(year, week))


def scrape_polls_for_year(year):
    fp = f'../build/cfb/polls/rcfb/{year}'
    if not os.path.exists(fp):
        os.mkdir(fp)
    url = f'https://poll.redditcfb.com/poll/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, features='html.parser')
    table = soup.find('h3', text=year).find_next_sibling()
    for tr in table.find_all('tr')[2:]:
#         print(tr)
        link = tr.find('a')
        print(link.text)
        poll_id = link['href'].split('/')[-2]
        match = re.match(r'Week (\d+)', link.text)
        if match:
            folder = match.group(1)
        else:
            folder = link.text

        fp = f'../build/cfb/polls/rcfb/{year}/{folder}'
        if not os.path.exists(fp):
            os.mkdir(fp)
            with open(f'{fp}/raw.csv', 'w') as outfile:
                writer = csv.writer(outfile)
                writer.writerows(voter.to_csv()
                                 for voter in scrape_ballots_for_poll_by_id(poll_id))

        
def scrape_characteristics_for_year(year):
    fp = f'../build/cfb/polls/rcfb/{year}'
    if not os.path.exists(fp):
        os.mkdir(fp)
    url = f'https://poll.redditcfb.com/poll/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, features='html.parser')
    table = soup.find('h3', text=year).find_next_sibling()
    for tr in table.find_all('tr')[2:]:
        link = tr.find('a')
        print(link.text)
        poll_id = link['href'].split('/')[-2]
        match = re.match(r'Week (\d+)', link.text)
        if match:
            folder = match.group(1)
        else:
            folder = link.text

        fp = f'../build/cfb/polls/rcfb/{year}/{folder}'
        if not os.path.exists(fp):
            os.mkdir(fp)
        with open(f'{fp}/characteristics.csv', 'w') as outfile:
            writer = csv.writer(outfile)
            writer.writerows(scrape_characteristics(poll_id))

        
def scrape_ballots_for_poll_by_id(poll_id, page_number=1):
    page = get_ballot_page_for_poll(poll_id, page_number)

    b = []

    btn_text = '\n                    Go to page...\n                '
    page_list = page.find('button', text=btn_text).find_next_sibling()
    num_pages = len(page_list.find_all('li'))

    for pn in tqdm(range(1, num_pages + 1)):
        b += scrape_ballots_from_page(page)
        page = get_ballot_page_for_poll(poll_id, pn + 1)

    return b
#     if is_last_page(page, page_number):
#         return scrape_ballots_from_page(page)
#     else:
#         b = scrape_ballots_from_page(page)
#         return b + scrape_ballots_for_poll_by_id(poll_id, page_number=page_number + 1)


def get_characteristics_from_link(link):
    return [('HUMAN' if 'text-primary' in link['class'] else
             'COMPUTER' if 'text-danger' in link['class'] else
             'HYBRID' if 'text-success' in link['class'] else
             None),
            (True if 'fw-bold' in link['class'] else
             False if 'fw-normal' in link['class'] else None)
            ]


def scrape_characteristics(poll_id):
    page = get_page_of_type_for_poll('voters', poll_id, {})
    main_voters = page.find('div', {'id': 'main-voters'})
    return [[link.text.strip(), *get_characteristics_from_link(link)]
            for link in main_voters.find_all('a')]


def scrape_ballots_from_page(page):
    table = page.find('table')
    rows = table.find_all('tr')
    ballots = [Voter(cell.text.strip(), 'reddit', rankings=[])
               for cell in rows[0].find_all('td')]
    for r, row in enumerate(rows[1:]):
        for p, cell in enumerate(row.find_all('td')):
            ballots[p].rankings.append(cell.text.strip())

    return ballots

