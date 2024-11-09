import matplotlib.pyplot as plt
import numpy as np
from math import floor
import cfbd
from core.authorize import create_client


def chart_game(game_id):
    client = create_client()
    metrics = cfbd.MetricsApi(client)
    wp_data = metrics.get_win_probability_data(game_id)

    x = np.linspace(0, 4, len(wp_data))
    y = [point.home_win_prob for point in wp_data]
    
    plt.figure()
    plt.plot(x, y)

    plt.plot(np.linspace(0, 4, 2), [0.5, 0.5])
    plt.axis([0, 4, 0, 1])
    plt.xticks([])
    plt.show()


def main():
    chart_game('401628511')


if __name__ == '__main__':
    main()
