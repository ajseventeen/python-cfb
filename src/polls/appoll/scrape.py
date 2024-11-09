from polls.analysis import Voter, Team
from bs4 import BeautifulSoup
from tqdm import tqdm
import requests
import urllib


# AP Poll

def get_ap_poll_page(week=None, voter=None, org=None, league='football'):
    url = f'https://apnews.com/hub/ap-top-25-college-{league}-poll'
    params = {}
    if voter:
        params['voter'] = voter
    if org:
        params['organization'] = org

    response = requests.get(url, params=urllib.parse.urlencode(params, quote_via=urllib.parse.quote))
    soup = BeautifulSoup(response.text, features='html.parser')
    return soup



def get_ap_poll_voters(week=None):

    '''
    returns a list of voters in the given week's poll.  Voters are represented
    by a Voter object.
    '''

    overall = get_ap_poll_page(week=week)
    voter_list = get_voter_list(overall)
    rankings = get_rankings_from_page(overall)

    for voter in tqdm(voter_list):
        voter.rankings = get_rankings_from_page(get_ap_poll_page(
            week=week, voter=voter.name, org=voter.organization
            ))

    return voter_list


def get_voter_list(soup):
    voter_select = soup.find('select', {'name': 'Select-pollster-input'})
    return [Voter(option['value'], option['data-org-name'])
            for option in voter_select.find_all('option')
            if option['value'] != '']


def get_rankings_from_page(soup):
    results = soup.find('div', {'class': 'Results-container'})
    team_list = results.find_all('dd', {'class': 'PollModuleRow'})
    team_names = [team.find('div',
                      {'class': 'PollModuleRow-team'}
                      )
            for team in team_list]
    return [team.find('a').text if team.find('a') else team.find('span').text for team in team_names]


# College Poll Tracker may be an easier way to get all of the data at once.

def get_college_poll_tracker_for_week(year, week, league='football'):
    week_text = 'pre-season' if week == 1 else f'week-{week}'
    cpt_url = f'https://collegepolltracker.com/{league}/grid/{year}/{week_text}'
    response = requests.get(cpt_url)
    soup = BeautifulSoup(response.text, features='html.parser')
    return soup


def get_voters_from_CPT(page):
    table = page.find('div', {'id': 'gridBallots'})
    return [get_voter_from_row(row)
            for row in table.find_all('div', {'class': 'gridRow'})
            if len(row.find_all('img')) > 0]
    

def get_voter_from_row(row):
    voter_div = row.find('div', {'class': 'gridPollster'})
    rankings = [img['title'] for img in row.find_all('img')]
    return Voter(voter_div.find('a').text,
                 voter_div.find('span').text,
                 rankings)


def scrape_ballots_for_poll(year, week, source='CPT', league='football'):
    if source == 'AP':
        return get_ap_poll_voters(week=week, league=league)
    elif source == 'CPT':
        page = get_college_poll_tracker_for_week(year, week, league=league)
        return get_voters_from_CPT(page)

