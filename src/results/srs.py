from core.cfbd import CFBD
from numpy import linalg


def avg(items):
    return sum(items) / len(items)


def get_team_score(game, team):
    return game.home_points if game.home_team == team else game.away_points


def get_opponent_score(game, team):
    return game.home_points if game.away_team == team else game.away_points


def get_margin(game, team, min_margin=0, max_margin=999):
    margin = get_team_score(game, team) - get_opponent_score(game, team)
    adj_margin = max(min(abs(margin), max_margin), min_margin)
    if margin > 0:
        return adj_margin
    elif margin < 0:
        return -1 * adj_margin
    else:
        return 0


def get_opponent(game, team):
    return game.home_team if game.away_team == team else game.away_team


def are_different(r1, r2, delta=0.001):
    return any(abs(r1[s] - r2[s]) > delta for s in r1.keys())


def should_include(game, include_fcs):
    if game.home_points is None:
        return False
    if include_fcs:
        return game.home_team != 'fcs' or game.away_team != 'fcs'
    else:
        return game.home_team != 'fcs' and game.away_team != 'fcs'


def get_srs(year, min_margin=0, max_margin=999, max_iter=9999,
            include_fcs=True, normalized=False):
    games = CFBD.get_games(year)
    teams = CFBD.get_fbs_teams()
    schools = [team.school for team in teams]
    if include_fcs:
        schools += ['fcs']

    for game in games:
        if game.away_team not in schools:
            game.away_team = 'fcs'
        if game.home_team not in schools:
            game.home_team = 'fcs'
    games = [g for g in games if should_include(g, include_fcs)]

    team_games = {school: [g for g in games
                           if ((g.home_team == school or
                                g.away_team == school))]
                  for school in schools}
    opponents = {school: [get_opponent(game, school)
                          for game in team_games[school]]
                 for school in schools}

    margins = {school: avg([get_margin(game, school, min_margin=min_margin,
                                       max_margin=max_margin)
                           for game in team_games[school]])
               for school in schools}

    # linalg solution

    coeff = [[len([x for x in opponents[school] if s == x]) for s in schools]
             for school in schools]
    for r, row in enumerate(coeff):
        total = sum(row)
        for i in range(len(row)):
            row[i] = row[i] / total
        row[r] = -1

    const = [-1*margins[school] for school in schools]

    ratings = linalg.solve(coeff, const)

    if normalized:
        xbar = sum(ratings) / len(ratings)
        ratings = [r - xbar for r in ratings]

    return {schools[n]: ratings[n] for n in range(len(ratings))}

#     ratings = margins.copy()
#     print(margins)
#     adj_ratings = {school: margins[school] + avg([ratings[s]
#                                                  for s in opponents[school]])
#                    for school in schools}
# 
#     iters = 0
#     while iters < max_iter and are_different(ratings, adj_ratings):
#         iters += 1
#         ratings = adj_ratings
#         adj_ratings = {school: margins[school] + avg([ratings[s]
#                                                      for s in opponents[school]])
#                        for school in schools}
# 
#     return adj_ratings

