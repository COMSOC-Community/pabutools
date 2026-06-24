from flask import render_template
from flask_example import app

import matplotlib.pyplot as plt, numpy as np
import io, base64
import networkx as nx

plt.switch_backend('agg')  # Non-interactive backend for saving PNG images

def plt_to_base64():
    iobytes = io.BytesIO()
    # plt.savefig("flask_example/static/fig.png", format='png')
    plt.savefig(iobytes, format='png')
    iobytes.seek(0)
    return base64.b64encode(iobytes.read()).decode()

@app.route('/')
def plot():
    x = np.linspace(0, 10, 100)
    plt.cla()
    plt.plot(x, np.sin(x))
    img_data = plt_to_base64()
    # print(len(img_data))
    return render_template('1-image.html', img_data=img_data)


@app.route('/animate')
def plot_animate():
    x = np.linspace(0, 10, 100)
    images_data = []
    for a in [-1, -0.5, -0.1, 0.1, 0.5, 1, 0.5, 0.1, -0.1, -0.5]:
        plt.cla()
        plt.plot(x, a * np.sin(x))
        plt.ylim(-1,1)
        images_data.append(plt_to_base64())

    return render_template('animate.html', images_data=images_data)


@app.route('/graph')
def graph():
    G = nx.complete_graph(7)
    plt.cla()
    nx.draw(G)
    img_data = plt_to_base64()
    return render_template('1-image.html', img_data=img_data)
