from core.authorize import create_client
import cfbd

client = create_client()

games_api = cfbd.GamesApi(client)

bluebloods = ['Michigan', 'Texas', 'USC', 'Nebraska',
              'Oklahoma', 'Ohio State', 'Alabama', 'Notre Dame']


def calculate_blueblood_results(year, week, api_games=None):
    wins = []
    losses = []
    ties = []
    if api_games is None:
        games = games_api.get_games(year, week=week)
    else:
        games = [g for g in api_games if g.week == week]

    for game in games:
        if game.home_team not in bluebloods and game.away_team not in bluebloods:
            continue

        if game.home_team in bluebloods:
            if game.home_points > game.away_points:
                wins.append(game.home_team)
            elif game.home_points < game.away_points:
                losses.append(game.home_team)
            else:
                ties.append(game.home_team)

        if game.away_team in bluebloods:
            if game.away_points > game.home_points:
                wins.append(game.away_team)
            elif game.away_points < game.home_points:
                losses.append(game.away_team)
            else:
                ties.append(game.away_team)

    return wins, losses, ties


