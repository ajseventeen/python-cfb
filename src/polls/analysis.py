from core.cfbd import CFBD
from reddit import get_flaired_name

from csv import reader, writer
from math import sqrt
from os.path import exists
import os

from tabulate import tabulate
from tqdm import tqdm


# numpy-ish things

def avg(values):
    return sum(values) / len(values)


def std(values):
    xbar = avg(values)
    return sqrt(avg([(x - xbar) ** 2 for x in values]))


def zscore(values):
    sigma = std(values)
    xbar = avg(values)
    return [0 if sigma == 0 else (x - xbar) / sigma for x in values]


class Voter:

    def __init__(self, name, organization, rankings=[]):
        self.name = name
        self.organization = organization
        self.rankings = rankings

    def __repr__(self):
        return self.name

    def get_unusualness_score(self, teams, top25):
        total_score = 0

        for r, team_name in enumerate(self.rankings):
            team = [t for t in teams if t.name == team_name][0]
            total_score += abs(get_vote_unusualness(r+1, team))

        for team in top25:
            if team.name not in self.rankings:
                total_score += get_exclusion_unusualness(team)

        self.unusualness = total_score
        return total_score

    def to_csv(self):
        return [self.name, self.organization, *self.rankings]

    @staticmethod
    def write_voters_to_csv(writer, voters):
        writer.writerows(Voter.to_csv() for voter in voters)

    @staticmethod
    def from_csv(line):
        return Voter(line[0], line[1], rankings=line[2:])


class Team:

    def __init__(self, name, voters=[]):
        self.name = name
        self.votes = [v.rankings.index(name) + 1 if name in v.rankings else 26
                      for v in voters]
        self.voter_count = len(voters)

    def __repr__(self):
        return self.name

    @property
    def vote_count(self):
        return len([v for v in self.votes if v != 26])

    @property
    def points(self):
        return sum(26 - vote for vote in self.votes)

    @property
    def ppv(self):
        return self.points / self.voter_count

    @property
    def std_dev(self):
        return std([vote for vote in self.votes if vote != 26])

    @property
    def rstd(self):
        return max(1, (self.std_dev * self.vote_count + self.ppv *
                       (self.voter_count - self.vote_count)) / self.voter_count)

    @property
    def zscores(self):
        real_votes = [x for x in self.votes if x != 26]
        z = zscore(real_votes)
        zscores = {}
        for rank, score in zip(real_votes, z):
            if rank not in zscores:
                zscores[rank] = score
        return zscores


def get_vote_unusualness(rank, team):
    points = 26 - rank
    z = (points - team.ppv) / team.rstd
    if z > 0:
        return max(0, z - 0.75)
    else:
        return min(0, z + 0.75)


def get_exclusion_unusualness(team):
    return max(0, team.ppv / team.rstd - 0.75)


def get_voter_differential(voter_ranking, teams, voter_count=60):
    diff = 0
    simple_diff = 0
    for pos, team_name in enumerate(voter_ranking):
        target_team = [t for t in teams if t.name == team_name][0]
        diff += abs((target_team.points) - (voter_count * (25 - pos)))
        simple_diff += abs(min(26, target_team.rank) - (pos + 1))

    return diff / 25, simple_diff / 25


def grade_voters(voters, teams):
    for voter in voters:
        diff, simple_diff = get_voter_differential(voter.rankings, teams,
                                               voter_count=len(voters))
        voter.diff = diff
        voter.simple_diff = simple_diff

    return voters


def get_voters_for_poll(fp, alt):
    if exists(fp):
        with open(fp, 'r') as infile:
            pollreader = reader(infile)
            return [Voter.from_csv(item) for item in pollreader]
    voters = alt()
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, 'w') as outfile:
        pollwriter = writer(outfile)
        pollwriter.writerows(voter.to_csv() for voter in voters)

        return voters


def td(text, is_formatted=False, is_header=False, left_border=False):
    tag = 'th' if is_header else 'td'
    if not is_formatted:
        if left_border:
            return f"<{tag} class=\"leftborder\">{text}</{tag}>"
        else:
            return f"<{tag}>{text}</{tag}>"

    content = text['n']
    cls = text['class']
    title = text.get('title', '')

    if left_border:
        cls += ' leftborder'
    return f'<{tag} class="numcell {cls}" title="{title}">{content}</{tag}>'


def th(text, **kwargs):
    return td(text, is_header=True, **kwargs)


def get_graphic_header(show_games=True):
    s = ''
    
    s += '<tr>'
    
    s += th('Rk')
    s += th('')
    s += th('Team')
    s += th('Points')

    if show_games:
        s += th('Previous', left_border=True)
        s += th('Next')

    for n in range(1, 26):
        s += th(n, left_border=n%5 == 1)

    s += th('U', left_border=True)

    s += '</tr>\n'
    return s


def get_game_description(game, team):
    if game is None:
        return '<img src="../../../../resources/bye.svg">'

    r = ''
    if game.away_team == CFBD.team_names.get(team, team):
        location = '<img src="../../../../resources/away.svg">'
        opponent_name = f'<img src="{CFBD.get_logo(game.home_team)}" title="{game.home_team}">'
    else:
        location = '<img src="../../../../resources/home.svg">'
        opponent_name = f'<img src="{CFBD.get_logo(game.away_team)}" title="{game.away_team}">'

    r += f'<div class="description">{location} {opponent_name}'

    if game.home_points is not None:
        did_win = CFBD.team_names.get(team, team) == (game.home_team if game.home_points > game.away_points
                           else game.away_team)
        result = 'W' if did_win else 'L'
        hi = max(game.home_points, game.away_points)
        lo = min(game.home_points, game.away_points)
        r += f' {result} {hi}-{lo}'

    r += '</div>'

    return r


def create_graphic(voters, **kwargs):
    logos = kwargs.get('logos', None)
    games = kwargs.get('games', None)
    show_games = kwargs.get('show_games', True)

    s = '<table>' + get_graphic_header(show_games=show_games)
    team_names = set([team for voter in voters for team in voter.rankings])
    teams = [Team(team, voters) for team in team_names]

    for r, team in enumerate(sorted(teams, key=lambda t: t.points, reverse=True)):
        rank = r + 1
        if (rank % 5 == 0):
            s += '<tr class="bottomborder">'
        else:
            s += '<tr>'

        s += td(rank)
        s += td(f'<img src="{CFBD.get_logo(team.name)}" title="{team.name}">')
        s += td(team.name)
        s += td(team.points)

        if show_games:
            s += td(get_game_description(games[team.name]['prev'], team.name),
                    left_border=True)
            s += td(get_game_description(games[team.name]['next'], team.name))

        cells = [{'n': len([v for v in team.votes if v == p]),
                  'voters': [v for v in voters if v.rankings[p-1] == team.name]
                            if p != 26 else
                            [v for v in voters if team.name not in v.rankings]}
                 for p in range(1, 27)]
        common = max(c['n'] for c in cells)
        for n, cell in enumerate(cells):
            cell['class'] = ''
            cell['title'] = ''
            if cell['n'] == 0:
                cell['class'] = 'none'
            elif cell['n'] == 1:
                cell['class'] = 'only'
                cell['title'] = cell['voters'][0].name if len(cell['voters']) == 1 else ''
            if cell['n'] == common:
                cell['class'] = 'most'
            if n == r and n < 25:
                cell['class'] = 'matches'
            s += td(cell, True, left_border=n%5 == 0)

        s += '</tr>\n'

    s += '</table>'

    return s


def build_team_list(ballots):
    teams = set([team for voter in voters for team in voter.rankings])
    return [Team(team, voters) for team in teams]


def analyze_poll(voters, **kwargs):
    print_table = kwargs.get('print_table', True)
    print_comment = kwargs.get('print_comment', True)
    all_ballots = kwargs.get('all_ballots', None)

    s = ''
    teams = set([team for voter in voters for team in voter.rankings])
    team_name_len = max(len(t) for t in teams) + 2
    team_list = [Team(team, voters) for team in teams]
    top25 = sorted(team_list, key=lambda t: t.points, reverse=True)[:25]

    for rank, t in enumerate(sorted(team_list, key=lambda x: x.points, reverse=True)):
        t.rank = len([tm for tm in team_list if tm.points > t.points]) + 1

        if print_table:
            s += f"{rank+1:>2d}. {t.name:<{team_name_len}s} ({t.ppv:>5.2f} / {t.rstd:>5.2f})  "
            for n in range(1, 27):
                l = len([x for x in t.votes if x == n])
                l = '--' if l == 0 else f'{l:>2d}'
                s += f'{l}'
                if n%5 == 0:
                    s += '| '
            s += '\n'

    graded = grade_voters(voters, team_list)

    votes = []
    for rank, voter in enumerate(sorted(graded, key=lambda x: x.diff)):
        for pos, team_name in enumerate(voter.rankings):
            team = [t for t in team_list if t.name == team_name][0]
            votes.append({
                'voter': voter,
                'position': pos+1,
                'team': team,
                'u': get_vote_unusualness(pos+1, team)
                })

        for r, team in enumerate(top25):
            if team.name not in voter.rankings:
                u = get_exclusion_unusualness(team)
                if u > 0:
                    votes.append({
                        'voter': voter,
                        'position': 'NR',
                        'team': team,
                        'u': get_exclusion_unusualness(team)
                        })
    u_scores = {voter.name: voter.get_unusualness_score(team_list, top25)
                for voter in graded}

    if print_comment:
        # Printing comment for Reddit
        s += ("\nA few interesting statistics for this week\'s votes:\n")
#               "Computations follow the same methods as the [r/CFB"
#               " Poll](https://poll.redditcfb.com/), so they don't always match"
#               " perfectly with the numbers in the graphic, but they are close"
#               " enough that the general impression is the same.\n")

        s += ('\n# Most Confusing Teams\n\n')
        s += (tabulate([[rank+1, get_flaired_name(team), team.rstd]
                        for rank, team in enumerate(sorted(team_list, key=lambda x:
                                                           x.rstd, reverse=True))][:5],
                       ['Rank', 'Team', 'Std. Dev.'],
                       tablefmt='pipe', floatfmt='5.2f'))
        s += '\n'

        s += ('\n# Most Unusual Ballots\n')
        s += '\n'
        s += (tabulate([[rank+1, voter.name, u_scores[voter.name]]
                        for rank, voter in enumerate(sorted(graded, key=lambda v:
                                                           u_scores[v.name],
                                                           reverse=True))][:5],
                       ['Rank', 'Voter', 'Unusualness'],
                       tablefmt='pipe', floatfmt='5.2f'))
        s += '\n'

        s += ('\n# Least Unusual Ballots\n')
        s += '\n'
        s += (tabulate([[rank+1, voter.name, u_scores[voter.name]]
                        for rank, voter in enumerate(sorted(graded, key=lambda v:
                                                           u_scores[v.name]))][:5],
                       ['Rank', 'Voter', 'Unusualness'],
                       tablefmt='pipe', floatfmt='5.2f'))
        s += '\n'

        s += ('\n# Largest Single-Vote Outliers\n')
        s += '\n'
        s += (tabulate([[rank+1, vote['voter'].name, get_flaired_name(vote['team']),
                        vote['position'], vote['u']]
                       for rank, vote in enumerate(sorted(votes, key=lambda x:
                                                          abs(x['u']),
                                                          reverse=True)[:5])],
                       ['Rank', 'Voter', 'Team', 'Position', 'Unusualness'],
                       tablefmt='pipe', floatfmt='5.2f'))
        s += '\n'

        s += ('\n# Teams ranked by PPV position\n')
        s += '\n'
        s += ('Thanks to u/MrTheSpork for [the idea](https://old.reddit.com/'
              'r/CFB/comments/1g4b62p/2024_week_8_rcfb_poll_1_texas_2_oregon_3'
              '_penn/ls21isy/)\n')
        s += '\n'
        s += ppv_table(team_list)
        s += '\n'

        if all_ballots:
            s += analyze_ballots_for_season(all_ballots)

        s += ('\n^(Let me know if there are any other metrics or data points that'
        ' you think would be interesting to include!)')

    return s


def ppv_table(teams):
    rankings = [[r, ' '.join([get_flaired_name(t)
                     for t in teams if round(t.ppv) == 26 - r])]
                for r in range(1, 26)]
    return tabulate(rankings,
                   ['Avg. Rank', 'Teams'],
                   tablefmt='pipe')


def analyze_ballots_for_season(ballot_list, ratio = 0.5):
    s = ''
    voters = set([voter.name for voter in ballot_list])

    collections = [{'ballots': [b for b in ballot_list if b.name == voter],
                    'voter': voter} for voter in voters]

    for v in collections:
        v['u'] = sum([b.unusualness for b in v['ballots']]) / len(v['ballots'])

    qual = ratio * max(len(c['ballots']) for c in collections)
    qualified = [c for c in collections
                 if len(c['ballots']) >= qual]
    s += ('\n-----')
    s += '\n'
    s += ('\nAnd some cumulative season stats:')
    s += '\n'
    s += (f'\n^(Must have submitted at least {qual} ballots)')
    s += '\n'
    s += ("\n# Most Unusual Voters\n")
    s += '\n'
    s += (tabulate([[rank+1, v['voter'], v['u'], len(v['ballots'])]
                    for rank, v in enumerate(sorted(qualified, key=lambda v:
                                                    v['u'],
                                                    reverse=True)[:5])],
                    ['Rank', 'Voter', 'Avg. Unusualness', 'Ballots'],
                   tablefmt='pipe', floatfmt='5.2f'))
    s += '\n'

    s += ("\n# Least Unusual Voters\n")
    s += '\n'
    s += (tabulate([[rank+1, v['voter'], v['u'], len(v['ballots'])]
                    for rank, v in enumerate(sorted(qualified, key=lambda v:
                                                    v['u'])[:5])],
                    ['Rank', 'Voter', 'Avg. Unusualness', 'Ballots'],
                   tablefmt='pipe', floatfmt='5.2f'))
    s += '\n'

    return s


def get_condorcet_score(a, b, voters):
    counts = [0, 0]
    for voter in voters:
        if a not in voter.rankings:
            if b in voter.rankings:
                counts[1] += 1
        else:
            if b not in voter.rankings:
                counts[0] += 1
            counts[1 if voter.rankings.index(a) > voter.rankings.index(b) else 0] += 1
    return counts


def get_smith_set(rankings):
    teams = list(set([t for b in rankings for t in b]))
    rng = range(len(teams))
    scores = [[0 for _ in teams] for _ in teams]
    for ranking in rankings:
        mask = [[0 for _ in teams] for _ in teams]
        for team in ranking:
            for i in rng:
                if mask[teams.index(team)][i] == 0 and i != teams.index(team):
                    mask[teams.index(team)][i] = 1
                    mask[i][teams.index(team)] = -1
        for r in rng:
            for c in rng:
                scores[r][c] += mask[r][c]

    scores = [[(1 + max(min(s, 1), -1)) / 2 for s in r] for r in scores]
#     print('\n'.join([' '.join(str(x) for x in row) for row in scores]))

    hi = max(sum(scores[i]) for i in rng)
    copeland = [r for r in rng if sum(scores[r]) == hi]
    smith = []
    while len(copeland) > 0:
        smith += copeland
        copeland = []
        for n in smith:
            copeland += [i for i in rng if scores[i][n] == 1 and i not in smith]
        copeland = list(set(copeland))

    return [teams[i] for i in smith]


def get_condorcet_score(a, b, rankings):
    scores = {a: 0, b: 0}
    for ranking in rankings:
        if a in ranking and b not in ranking:
            scores[a] += 1
        elif a not in ranking and b in ranking:
            scores[b] += 1
        elif a in ranking and b in ranking:
            scores[a if ranking.index(a) < ranking.index(b) else b] += 1
    return scores


def get_smith_sets(voters):
    smith_sets = []
    rankings = [[x for x in voter.rankings] for voter in voters]
    while any(len(ranking) > 0 for ranking in rankings):
        smith_sets.append(get_smith_set(rankings))
        rankings = [[x for x in r if x not in smith_sets[-1]] for r in rankings]
#         for a in smith_sets[-1]:
#             for b in smith_sets[-1][smith_sets[-1].index(a)+1:]:
#                 scores = get_condorcet_score(a, b, [v.rankings for v in voters])
#                 h = a if scores[a] >= scores[b] else b
#                 l = a if h == b else b
#                 print(f'{h:>25s}: {scores[h]:>2d} {l:>25s}: {scores[l]:>2d}')


    return smith_sets
        

if __name__ == '__main__':
#     get_ap_poll_page.clear_cache()
#     get_ap_poll_voters.clear_cache()
    main()


