from polls.appoll import scrape as ap_scrape
from polls.rcfbpoll import scrape as rcfb_scrape
from core.cfbd import CFBD
from polls import analysis
from schedule import generate
from results import bluebloods, srs


from tabulate import tabulate
# import cfbd
import requests
import requests_cache
from core.authorize import create_client
from csv import DictReader
import os
from argparse import ArgumentParser
from tqdm import tqdm


# HTTP request caching
# requests_cache.install_cache('cfbd', expire_after=86400)


CFBD_TRANSLATIONS = {
        'Washington St': 'Washington State',
        'ULM': 'Louisiana-Monroe',
        'C Carolina': 'Coastal Carolina',
        'SDSU': 'San Diego State',
        'Miami (FL)': 'Miami',
        'ULM': 'UL Monroe',
        'Appalacian State': 'App State',
        }

RCFB_TRANSLATIONS = {
        'Washington State': 'Washington St',
        'Louisiana-Monroe': 'ULM',
        'Coastal Carolina': 'C Carolina',
        'San Diego State': 'SDSU',
        'Miami': 'Miami (FL)',
        }


def img(team_name):
    src = CFBD.get_logo(team_name)
    return f'<img src="{src}" alt="{team_name}" title="{team_name}">'


def get_game_description(game, team):
    if game is None:
        return '<img src="../../../../resources/bye.svg">'

    r = ''
    if game.away_team == team:
        location = '<img src="../../../../resources/away.svg">'
        opponent_name = img(game.home_team)
    else:
        location = '<img src="../../../../resources/home.svg">'
        opponent_name = img(game.away_team)

    r += f'<div class="description">{location} {opponent_name}'

    if game.home_points is not None:
        did_win = team == (game.home_team if game.home_points > game.away_points
                           else game.away_team)
        result = 'W' if did_win else 'L'
        hi = max(game.home_points, game.away_points)
        lo = min(game.home_points, game.away_points)
        r += f' {result} {hi}-{lo}'

    r += '</div>'

    return r


def get_graphic_for_week(year, week, **kwargs):
    poll = kwargs.get('poll', 'AP')
    league = kwargs.get('league', 'football')

    leaguestr = 'cfb' if league == 'football' else 'cbb' if league == 'basketball' else 'unknown'
    if poll == 'AP':
        scrapefn = lambda: ap_scrape.scrape_ballots_for_poll(year, week, league=league)
        polltext = 'ap'
    elif poll == 'r/CFB':
        scrapefn = lambda: rcfb_scrape.scrape_ballots_for_poll(year, week)
        polltext = 'rcfb'
    else:
        return ''

    fp = f'../build/{leaguestr}/polls/{polltext}/{year}/{week}/raw.csv'
    ballots = analysis.get_voters_for_poll(fp, scrapefn)
    team_names = set([t for voter in ballots for t in voter.rankings])
    logos = CFBD.build_logo_dict(team_names)
    
    games = CFBD.build_prev_next_dict(team_names, year, week)
    s = f'''
    <html lang="en">
    <head>
    <link rel="stylesheet" href="../../../../styles.css" />
    </head>
    <body>
    <h1>{poll} Poll Vote Distribution for Week {week}, {year}</h1>
    <div class="prevnext">
    '''

    if week > 1:
        s += f'<a href="../{week-1}/index.html">Previous Week</a>'
    if 1 < week < 15:
        s += ' | '
    if week < 15:
        s += f'<a href="../{week+1}/index.html">Next Week</a>'
    s += '</div>'

    s += analysis.create_graphic(ballots, logos=logos, games=games, **kwargs)
    s += '</body></html>'
    return s


def analyze_season_ballots(year, week, **kwargs):
    poll = kwargs.get('poll', 'AP')
    all_ballots = []

    for wk in range(1, week + 1):
        if poll == 'AP':
            scrapefn = lambda: ap_scrape.scrape_ballots_for_poll(year, week)
            pollstr = 'ap'
        elif poll == 'r/CFB':
            scrapefn = lambda: rcfb_scrape.scrape_ballots_for_poll(year, week)
            pollstr = 'rcfb'

        fp = f"../build/cfb/polls/{pollstr}/{year}/{wk}/raw.csv"
        ballots = analysis.get_voters_for_poll(fp, scrapefn)
        analysis.analyze_poll(ballots, print_table=False, print_comment=False, all_ballots=all_ballots, **kwargs)
        all_ballots += ballots

        if wk == week:
            return analysis.analyze_poll(ballots, print_table=False, print_comment=True, all_ballots=all_ballots)


def check_bluebloods():
    print('Year,Week,W,L,T,', end='')
    for team in bluebloods.bluebloods:
        print(team, end=',')
    for year in range(2023, 2000, -1):
        games = CFBD.get_games(year)
        for week in range(1, 16):
            w, l, t = bluebloods.calculate_blueblood_results(year, week, games)
            print(f"{year},{week},{len(w)},{len(l)},{len(t)},", end='')
            for team in bluebloods.bluebloods:
                print('W' if team in w else 'L' if team in l else
                      'T' if team in t else '-', end=',')
            print()


def get_last_ranking(start_at=1, in_rankings={}):
    most_recent = {}
    for year in range(2024, 1999, -1):
        rankings = CFBD.get_rankings(year) if year not in in_rankings else in_rankings[year]
        for ranking in sorted(rankings, key=lambda r: r.week, reverse=True):
            if (ranking.week < start_at):
                continue
            ap_polls = [p for p in ranking.polls if p.poll == 'AP Top 25']
            for poll in ap_polls:
                for rank in poll.ranks:
                    if rank.school not in most_recent:
                        most_recent[rank.school] = [year, ranking.week, rank.rank]

    return most_recent


def save_graphic_for_week(year, week, **kwargs):
    poll = kwargs.get('poll', 'AP')
    league = kwargs.get('league', 'football')
    show_games = kwargs.get('show_games', True)

    graphic = get_graphic_for_week(year, week, **kwargs)
    pollstr = 'ap' if poll == 'AP' else ('rcfb' if poll == 'r/CFB' else 'unknown')
    leaguestr = 'cfb' if league == 'football' else 'cbb' if league == 'basketball' else 'unknown'

    fp = f'../build/{leaguestr}/polls/{pollstr}/{year}/{week}/index.html'

    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, 'w') as outfile:
        outfile.write(graphic)


def get_poll_link(year, week, **kwargs):
    poll = kwargs.get('poll', 'AP')
    pollstr = 'ap' if poll == 'AP' else ('rcfb' if poll == 'r/CFB' else 'unknown')
    return f'https://ajseventeen.tech/cfb/polls/{pollstr}/{year}/{week}'


def create_post_for_week(year, week, **kwargs):
    poll = kwargs.get('poll', 'AP')
    pollstr = 'ap' if poll == 'AP' else ('rcfb' if poll == 'r/CFB' else 'unknown')
    s = f'''
[Week {week} table]({get_poll_link(year, week, poll=poll)})

Previous weeks:

'''
    for wk in range(week - 1, 0, -1):
        s += f'- [Week {wk}]({get_poll_link(year, wk, poll=poll)})\n'

    s += f'''
I am building off of the great work from u/Perryapsis, who has been creating
a similar visualization for the AP Poll for years.  The table shows the
votes for each team by position.  For any single votes, you can see the user
who submitted that vote by hovering over that cell of the table.

This is still very much a work-in-progress, and I always appreciate any
suggestions or feedback to make it more interesting!  The
[r/CFB Poll's website](https://poll.redditcfb.com) has all of the individual
ballots freely available, as well as an analytics page that contains some
interesting metrics.  All of my calculations below are using the same
methodology from the site, and several of these tables can also be found
there.

UPDATE: I've done some work on integrating these visuals into the poll website.
Still working on getting everything finalized, but hopefully this will be there
sooner or later (feel free to keep an eye on [this
PR](https://github.com/redditCFB/rcfbpoll3/pull/32) to monitor that progress).
Once that is up, you'll be able to filter by voter type and pre-/post-AP poll
release.

-----
'''

    s += analyze_season_ballots(year, week, poll=poll)

    return s


def get_results_for_team(team):
    played = [g for g in CFBD.get_games() if g.away_points is not None]
    home_games = [g for g in played if g.home_team == team]
    away_games = [g for g in played if g.away_team == team]

    wins = ([g.away_team for g in home_games if g.home_points > g.away_points] + 
            [g.home_team for g in away_games if g.away_points > g.home_points])
    losses = ([g.away_team for g in home_games if g.home_points < g.away_points] + 
            [g.home_team for g in away_games if g.away_points < g.home_points])

    return wins, losses


def print_srs_best_worst():
    with open('srs.csv', 'r') as infile:
        reader = DictReader(infile)
        teams = {
                t['School']: float(t['SRS']) for t in reader
                }

    ranks = {'---': 0}
    for n, item in enumerate(sorted(teams.items(), key=lambda x: x[1], reverse=True)):
        ranks[item[0]] = n + 1

    for team, rating in sorted(teams.items(), key=lambda x: x[1], reverse=True):
        wins, losses = get_results_for_team(team)

        best_win = sorted(wins, key=lambda x: teams.get(x, -100), reverse=True)[0] if len(wins) > 0 else '---'
        best_rank = ranks.get(best_win, 0)
        worst_loss = sorted(losses, key=lambda x: teams.get(x, 100))[0] if len(losses) > 0 else '---'
        worst_rank = ranks.get(worst_loss, 0)

        print(f"{team:<20s} | ({best_rank:>3d}) {best_win:<20s} | ({worst_rank:>3d}) {worst_loss:<20s}")


def do_ranking_things():
    rankings = {
            year: CFBD.get_rankings(year)
            for year in tqdm(range(2024, 1999, -1))
            }

    print({year: max(r.week for r in rankings[year]) for year in range(2024, 1999, -1)})

    by_week = {}
    for week in range(1, 18):
        recent = get_last_ranking(start_at=week, in_rankings=rankings)
        for team in CFBD.get_teams():
            if team.conference not in ['Big Ten', 'SEC', 'ACC', 'Big 12', 'Pac-12']:
                continue
            if team.school not in by_week:
                by_week[team.school] = []
            if team.school in recent:
                by_week[team.school].append(recent[team.school][0])
            else:
                by_week[team.school].append(0)

    for school, dates in by_week.items():
        print(school, end=',')
        for year in dates:
            print(year, end=',')
        print()


def get_record_before_week(team, week, games):
    previous_games = [g for g in games
                      if g.week < week
                      and (g.away_team == team or g.home_team == team)]
    record = [0, 0, 0]

    for g in previous_games:
        if ((g.away_team == team and g.away_points > g.home_points) or 
            (g.home_team == team and g.home_points > g.away_points)):
            record[0] += 1
        elif g.home_points == g.away_points:
            record[2] += 1
        else:
            record[1] += 1
    if (record[0] >= 5 and record[1] == 0):
        game = [g for g in games if g.week == week and (g.away_team == team or
                                                        g.home_team == team)][0]
    return record


def get_lopsided_matchups(year):
    games = [g for g in CFBD.get_games(year, division='fbs') if g.away_points is not None]

    lopsided_games = []
    tabledata = []

    for game in games:
        hw, hl, ht = get_record_before_week(game.home_team, game.week, games)
        aw, al, at = get_record_before_week(game.away_team, game.week, games)

#         print(aw, al, at)

        if ((hw >= 5 and hl == 0 and aw == 0 and al >= 5) or
            (hw == 0 and hl >= 5 and aw >= 5 and al == 0)):
            lopsided_games.append(game)
            tabledata.append([game.away_team, aw, al, at,
                              game.home_team, hw, hl, ht,
                              game.away_points, game.home_points,
                              'away' if game.away_points >
                              game.home_points else 'home' if
                              game.home_points > game.away_points else 'tie'])

    if len(tabledata) > 0:
        print(tabulate(tabledata,
                       ['Away', 'aW', 'aL', 'aT',
                        'Home', 'hW', 'hL', 'hT',
                        'aPts', 'hPts', 'Winner']))
        print()


def get_table(rowfn, items, headers, **kwargs):
    if 'tablefmt' not in kwargs:
        kwargs['tablefmt'] = 'pipe'

    if kwargs.get('with_ranks', True):
        _items = enumerate(items)
        _rowfn = lambda x: [x[0] + 1] + rowfn(x[1])
        _headers = ['Rank'] + headers
    else:
        _items = items
        _rowfn = rowfn
        _headers = headers

    return tabulate([_rowfn(item) for item in _items],
                    _headers,
                    **kwargs)


if __name__ == '__main__':
    parser = ArgumentParser(prog='CFB Python Tools',
                            description='A suite of tools for use with NCAA football data')

    parser.add_argument('command')

    parser.add_argument('-y', '--year', type=int, default=2024)
    parser.add_argument('--start-year', type=int)
    parser.add_argument('--end-year', type=int)

    parser.add_argument('-w', '--week', type=int, default=10)
    parser.add_argument('--start-week', type=int)
    parser.add_argument('--end-week', type=int)

    parser.add_argument('-l', '--league', default='football')
    parser.add_argument('-p', '--poll', default='AP')
    parser.add_argument('-s', '--source', default='CPT')

    parser.add_argument('--hide-games', action='store_true')

    parser.add_argument('--predefined', action='store_true')
    parser.add_argument('--max-margin', type=int, default=999)
    parser.add_argument('--min-margin', type=int, default=0)
    parser.add_argument('--normalized', action='store_true')
    parser.add_argument('--include-fcs', action='store_true')

    args = parser.parse_args()

    if args.poll == 'AP':
        scraper = ap_scrape
        scrapefn = lambda: ap_scrape.scrape_ballots_for_poll(year, week)
        polltext = 'ap'
    elif args.poll == 'r/CFB':
        scraper = rcfb_scrape
        scrapefn = lambda: rcfb_scrape.scrape_ballots_for_poll(year, week)
        polltext = 'rcfb'
    else:
        parser.error('Unknown poll specified.')

    # do stuff
    year_del = -1 if args.start_year and args.start_year > args.end_year else 1
    years = range(args.start_year, args.end_year + year_del, year_del) if args.start_year else [args.year]
    week_del = -1 if args.start_week and args.start_week > args.end_week else 1
    weeks = range(args.start_week, args.end_week + week_del, week_del) if args.start_week else [args.week]

    if args.command == 'check-bluebloods':
        check_bluebloods()

    elif args.command == 'print-srs':
        print_srs_best_worst()

    elif args.command == 'scrape-characteristics':
        for year in years:
            rcfb_scrape.scrape_characteristics_for_year(year)

    elif args.command == 'create-graphic':
        for year in years:
            for week in weeks:
                save_graphic_for_week(year, week, poll=args.poll, league=args.league, show_games=not args.hide_games)

    elif args.command == 'debug-graphic':
        for year in years:
            for week in weeks:
                get_graphic_for_week(year, week, poll=args.poll, league=args.league, show_games=not args.hide_games)

    elif args.command == 'create-post':
        for year in years:
            for week in weeks:
                print(create_post_for_week(year, week, poll=args.poll))

    elif args.command == 'create-comment':
        for year in years:
            for week in weeks:
                print(analyze_season_ballots(year, week, poll=args.poll))

    elif args.command == 'scrape':
        for year in years:
            for week in weeks:
                scraper.scrape_ballots_for_poll(year, week, source=args.source)

    elif args.command == 'smith-sets':
        sets = []
        for year in years:
            for week in weeks:
                fp = f'../build/cfb/polls/{polltext}/{year}/{week}/raw.csv'
                voters = analysis.get_voters_for_poll(fp, scrapefn)
                smith_sets = analysis.get_smith_sets(voters)
                sets.append(smith_sets)

        print(get_table(
            lambda x: [' '.join([analysis.get_flaired_name(e) for e in ss])
                       for ss in x],
            [[ss[n] if n < len(ss) else [] for ss in sets] for n in range(max(len(w) for w in sets))],
            [x+1 for x in range(len(sets))]))

    elif args.command == 'srs':
        for year in years:
            if args.predefined:
                ratings = srs.get_srs(year, normalized=args.normalized,
                                      include_fcs=args.include_fcs)
                cfbref = srs.get_srs(year, max_margin=24, min_margin=7,
                                     normalized=args.normalized,
                                     include_fcs=args.include_fcs)
                wl = srs.get_srs(year, max_margin=1, normalized=args.normalized,
                                 include_fcs=args.include_fcs)
                print(get_table(lambda x: [x[0], ratings[x[0]], x[1], wl[x[0]]],
                                sorted(cfbref.items(), key=lambda x: x[1], reverse=True),
                                ['Team', 'SRS', 'cfb-ref SRS', 'W/L Only']))
            else:
                ratings = srs.get_srs(year, max_margin=args.max_margin,
                                      min_margin=args.min_margin,
                                      normalized=args.normalized,
                                      include_fcs=args.include_fcs)
                print(get_table(lambda x: [x[0], x[1]],
                                sorted(ratings.items(), key=lambda x: x[1], reverse=True),
                                ['Team', 'SRS']))

    elif args.command == 'debug':
        for year in years:
            for week in weeks:
                print(f'Year: {year:>4d}   Week: {week:>2d}')

    else:
        parser.error('Unknown command.')

        
# for year in range(2023, 2010, -1):
#     rcfb_scrape.scrape_characteristics_for_year(year)

# rcfb_scrape.scrape_characteristics_for_year(2024)

# print_srs_best_worst()

# check_bluebloods()

# get_graphic_for_week(2024, 10, 'AP')

# for key, value in get_last_ranking().items():
#     print(f"{key:<25s} | {value[0]} | {value[1]:>2d} | {value[2]:>2d}")


# for week in range(1, 9):
#     save_graphic_for_week(2024, week, 'r/CFB')

# save_graphic_for_week(2024, 10, 'r/CFB')
# print(analyze_season_ballots(2024, 10, 'r/CFB'))
# print(get_graphic_for_week(2024, 10, 'r/CFB'))

# print(create_post_for_week(2024, 10, 'r/CFB'))

# for year in range(2016, 2010, -1):
#     print(f'YEAR: {year}\n')
#     rcfb_scrape.scrape_polls_for_year(year)

# for year in range(1980, 1920, -1):
#     print(f'# YEAR: {year}')
#     get_lopsided_matchups(year)

# TEMP
# ballots = analysis.get_voters_for_poll(f'polls/appoll/results/2024/week9.csv',
#                               lambda: ap_scrape.scrape_ballots_for_poll(2024, 9, source='AP'))
# 
# print(analysis.analyze_poll(ballots, True))

