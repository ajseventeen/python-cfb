from core.authorize import create_client

import cfbd


YEAR = 2024


class CFBD:
    
    client = create_client()
    games_api = cfbd.GamesApi(client)
    teams_api = cfbd.TeamsApi(client)
    rankings_api = cfbd.RankingsApi(client)

    team_names = {
            'Washington St': 'Washington State',
            'ULM': 'Louisiana-Monroe',
            'C Carolina': 'Coastal Carolina',
            'SDSU': 'San Diego State',
            'Miami (FL)': 'Miami',
            'ULM': 'UL Monroe',
            'Appalacian State': 'App State',
            'NDSU': 'North Dakota State',
            'WKU': 'Western Kentucky',
            }

    logo_urls = {
            'Charlotte': 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/ncaa/500/2429.png&h=200&w=200',
            }


    # Direct API calls
    #
    # Using persistent_cache to store the results

    @staticmethod
    def get_teams(*args, **kwargs):
        return CFBD.teams_api.get_teams(*args, **kwargs)

    @staticmethod
    def get_fbs_teams(*args, **kwargs):
        return CFBD.teams_api.get_fbs_teams(*args, **kwargs)

    @staticmethod
    def get_games(*args, **kwargs):
        return CFBD.games_api.get_games(*args, **kwargs)

    @staticmethod
    def get_rankings(*args, **kwargs):
        return CFBD.rankings_api.get_rankings(*args, **kwargs)


    # Useful methods

    @staticmethod
    def build_logo_dict(team_names):
        CFBD.logo_urls = {
                t.school: CFBD.logo_urls.get(t.school, t.logos[0] if t.logos else None)
                for t in CFBD.get_teams()
                }
        return {
                team: CFBD.logo_urls.get(CFBD.team_names.get(team, team), None)
                for team in team_names
                }

    @staticmethod
    def get_logo(team):
        return CFBD.logo_urls.get(CFBD.team_names.get(team, team), None)

    @staticmethod
    def get_team_game_by_week(team_name, year, week):
        all_games = CFBD.get_games(year, week=week)
        matches = [g for g in all_games
                   if g.away_team == team_name or g.home_team == team_name]
        return None if len(matches) == 0 else matches[0]

    @staticmethod
    def build_prev_next_dict(team_names, year, week):
        games = {}
        for team_name in team_names:
            name = CFBD.team_names.get(team_name, team_name)

            if week > 1:
                prev = CFBD.get_team_game_by_week(name, year, week-1)
            else:
                prev = None
            _next = CFBD.get_team_game_by_week(name, year, week)

            games[team_name] = {'prev': prev, 'next': _next}

        return games


