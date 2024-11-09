
def get_flaired_name(team):
    if isinstance(team, str):
        n = team
    else:
        n = team.name
    if n == 'Miami (FL)':
        return '[Miami (FL)](#f/miami)'
    if n == 'Texas A&M':
        return '[Texas A&M](#f/texasam)'
    if n == 'Washington St':
        return '[Washington State](#f/washingtonstate)'
    if n == 'NDSU':
        return '[NDSU](#f/northdakotastate)'
    if n == 'UConn':
        return '[UConn](#f/connecticut)'
    return f"[{n}](#f/{n.lower().replace(' ', '')})"


