from flask import Flask, jsonify, send_file
from flask_cors import CORS
from config import config
import psycopg2 as ps
from bokeh.plotting import figure, save, show
from bokeh.io import output_file
from bokeh.models import ColumnDataSource, ColorBar, LabelSet, TabPanel, Tabs, Range1d
from bokeh.transform import linear_cmap
from bokeh.palettes import Reds, OrRd
import pandas as pd
import math
import matplotlib.pyplot as plt
import seaborn as sns
import io
import numpy as np

app = Flask(__name__)
CORS(app)
df_pitcher = 0
df_batter = 0

rel_path = '/home/GT-Baseball-VIP/db_scripts'

conn = None


#THIS WORKS 
@app.route('/api/<teamCode>/pitchers', methods=['GET'])
#def get_pitchers(team_code='GIT_YEL',batter_or_pitcher='pitcher'):
def get_pitchers(teamCode='GIT_YEL'):
    conn = None
    try:
        conn = ps.connect(host = "172.18.50.2",
                database = "all_games",
                user = "postgres",
                password = "[AjayPagan12!]")
        cur = conn.cursor()
        #cur.execute("SELECT DISTINCT pitcher from allgames WHERE pitcherteam='{team_code}'".format(batter_or_pitcher=batter_or_pitcher,team_code=team_code))
        cur.execute("SELECT DISTINCT pitcher from allgames WHERE pitcherteam = '{teamCode}'".format(teamCode=teamCode))
        pitchers = cur.fetchall()
        pitcher_list = [pitcher[0] for pitcher in pitchers]
        return jsonify(pitcher_list)
    except Exception as e:
        print(f"Error{e}")
        return {"error":'An error occurred'}, 500
    finally:
        if conn is not None:
            conn.close()

@app.route('/api/<teamCode>/batters', methods=['GET'])
#def get_pitchers(team_code='GIT_YEL',batter_or_pitcher='pitcher'):
def get_batters(teamCode='GIT_YEL'):
    conn = None
    try:
        conn = ps.connect(host = "172.18.50.2",
                database = "all_games",
                user = "postgres",
                password = "[AjayPagan12!]")
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT batter from allgames WHERE pitcherteam = '{teamCode}'".format(teamCode=teamCode))
        batters = cur.fetchall()
        batter_list = [batter[0] for batter in batters]
        return jsonify(batter_list)
    except Exception as e:
        print(f"Error{e}")
        return {"error":'An error occurred'}, 500
    finally:
        if conn is not None:
            conn.close()

@app.route('/api/pitcher/<selectedPitcher>/heatmap/<batterSide>')
def get_heatmap_pitcher(selectedPitcher,batterSide):
    try:
        conn = ps.connect(host = "172.18.50.2",
                database = "all_games",
                user = "postgres",
                password = "[AjayPagan12!]")
        cur = conn.cursor()

        ##NEED THESE TWO LINES TO TEST THE BACKEND
        #selectedPitcher = selectedPitcher.replace(",", ", ")
        #print('This is the pitcher:', selectedPitcher)
        ##NEED THESE TWO LINES TO TEST THE BACKEND

        query = None
        if batterSide == 'Both':
            query = "SELECT * FROM allgames WHERE (pitcher = '{selectedPitcher}')".format(selectedPitcher=selectedPitcher)
        else:
            query = "SELECT * FROM allgames WHERE (pitcher = '{selectedPitcher}' AND batterside = '{batterSide}')".format(selectedPitcher=selectedPitcher, batterSide=batterSide)
        cur.execute(query)
        result = cur.fetchall()
        column_names = [desc[0] for desc in cur.description]
        global df_pitcher
        df_pitcher = pd.DataFrame(result, columns=column_names)
        df_pitcher['hc_x'] = df_pitcher['distance'] * np.cos(np.pi * (90 - df_pitcher['bearing']) / 180)
        df_pitcher['hc_y'] = df_pitcher['distance'] * np.sin(np.pi * (90 - df_pitcher['bearing']) / 180)
        df_pitcher['direction_radians'] = np.radians(df_pitcher['direction'])
        df_pitcher.loc[(df_pitcher['taggedhittype'] == 'GroundBall') & (df_pitcher['exitspeed'] > 50), 'distance'] += 70

        # Calculate x and y coordinates
        df_pitcher['x'] = df_pitcher['distance'] * np.sin(df_pitcher['direction_radians'])
        df_pitcher['y'] = df_pitcher['distance'] * np.cos(df_pitcher['direction_radians'])
        df_pitcher= df_pitcher[df_pitcher['pitchcall'] == 'InPlay']
        df_pitcher= df_pitcher[df_pitcher['distance'] >= 0]
        df_pitcher= df_pitcher[df_pitcher['pitchcall'] == 'InPlay']
        df_pitcher = df_pitcher[df_pitcher['y'] >= 0]


        #NOW ONTO THE HEATMAP CREATION
        # Set up plot with baseball field dimensions
        plt.figure(figsize=(10, 8))
        # Plot the heatmap for all hits first
        sns.kdeplot(x=df_pitcher['x'], y=df_pitcher['y'], cmap='Reds', fill=True, thresh=0.05, alpha=0.8)
        plt.title('{selectedPitcher} Heatmap vs {batterSide}-Handed Batters'.format(selectedPitcher = selectedPitcher, batterSide=batterSide)) # this needs to change (the name at least)

        # Set the original limits for the baseball field dimensions
        plt.xlim(-100, 100)
        plt.ylim(-10, 425)

        # Plot the bases as black squares with real-world coordinates
        plt.scatter(0, 0, color='black', s=100, label="Home Plate")
        plt.scatter(45, 60.5, color='black', s=100, label="First Base")
        plt.scatter(0, 127.28, color='black', s=100, label="Second Base")
        plt.scatter(-45, 60.5, color='black', s=100, label="Third Base")

        # Draw lines between the bases to complete the field
        plt.plot([0, 45], [0, 60.5], color='black')
        plt.plot([45, 0], [60.5, 127.28], color='black')
        plt.plot([0, -45], [127.28, 60.5], color='black')
        plt.plot([-45, 0], [60.5, 0], color='black')

        plt.plot([0, 100], [0, 140], color='red', linestyle='--', label="Foul Line (1st Base Side)")
        plt.plot([0, -100], [0, 140], color='red', linestyle='--', label="Foul Line (3rd Base Side)")
        # Draw a dotted ring for the infield (expand the oval to reach 400 feet)


        # Optional: Add a legend for base locations and the end points
        #plt.legend()

        # Show the plot
        #plt.show()
        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        return send_file(img, mimetype='image/png')

    except Exception as e:
        return {"error":'An error occurred'},500
    finally:
        if conn is not None:
            conn.close()


@app.route('/api/batter/<selectedBatter>/heatmap/<pitcherSide>')
def get_heatmap_batter(selectedBatter,pitcherSide):
    try:
        conn = ps.connect(host = "172.18.50.2",
                database = "all_games",
                user = "postgres",
                password = "[AjayPagan12!]")
        cur = conn.cursor()

        # #NEED THESE TWO LINES TO TEST THE BACKEND
        # selectedPitcher = selectedPitcher.replace(",", ", ")
        # print('This is the pitcher:', selectedPitcher)
        # #NEED THESE TWO LINES TO TEST THE BACKEND
        query = None
        if pitcherSide == 'Both':
            query = "SELECT * FROM allgames WHERE (batter = '{selectedBatter}')".format(selectedBatter=selectedBatter)
        else:
            query = "SELECT * FROM allgames WHERE (batter = '{selectedBatter}' AND pitcherthrows = '{pitcherSide}')".format(selectedBatter=selectedBatter, pitcherSide=pitcherSide)

        cur.execute(query)
        result = cur.fetchall()
        column_names = [desc[0] for desc in cur.description]
        global df_batter
        df_batter = pd.DataFrame(result, columns=column_names)
        df_batter['hc_x'] = df_batter['distance'] * np.cos(np.pi * (90 - df_batter['bearing']) / 180)
        df_batter['hc_y'] = df_batter['distance'] * np.sin(np.pi * (90 - df_batter['bearing']) / 180)
        df_batter['direction_radians'] = np.radians(df_batter['direction'])
        df_batter.loc[(df_batter['taggedhittype'] == 'GroundBall') & (df_batter['exitspeed'] > 50), 'distance'] += 70

        # Calculate x and y coordinates
        df_batter['x'] = df_batter['distance'] * np.sin(df_batter['direction_radians'])
        df_batter['y'] = df_batter['distance'] * np.cos(df_batter['direction_radians'])
        df_batter= df_batter[df_batter['pitchcall'] == 'InPlay']
        df_batter= df_batter[df_batter['distance'] >= 0]
        df_batter= df_batter[df_batter['pitchcall'] == 'InPlay']
        df_batter = df_batter[df_batter['y'] >= 0]
    

        #NOW ONTO THE HEATMAP CREATION
        # Set up plot with baseball field dimensions
        plt.figure(figsize=(10, 8))
        # Plot the heatmap for all hits first
        sns.kdeplot(x=df_batter['x'], y=df_batter['y'], cmap='Reds', fill=True, thresh=0.05, alpha=0.8)
        plt.title('{selectedBatter} Heatmap vs {pitcherSide}-Handed Pitchers'.format(selectedBatter = selectedBatter, pitcherSide=pitcherSide)) # this needs to change (the name at least)

        # Set the original limits for the baseball field dimensions
        plt.xlim(-100, 100)
        plt.ylim(-10, 425)

        # Plot the bases as black squares with real-world coordinates
        plt.scatter(0, 0, color='black', s=100, label="Home Plate")
        plt.scatter(45, 60.5, color='black', s=100, label="First Base")
        plt.scatter(0, 127.28, color='black', s=100, label="Second Base")
        plt.scatter(-45, 60.5, color='black', s=100, label="Third Base")

        # Draw lines between the bases to complete the field
        plt.plot([0, 45], [0, 60.5], color='black')
        plt.plot([45, 0], [60.5, 127.28], color='black')
        plt.plot([0, -45], [127.28, 60.5], color='black')
        plt.plot([-45, 0], [60.5, 0], color='black')

        plt.plot([0, 100], [0, 140], color='red', linestyle='--', label="Foul Line (1st Base Side)")
        plt.plot([0, -100], [0, 140], color='red', linestyle='--', label="Foul Line (3rd Base Side)")
        # Draw a dotted ring for the infield (expand the oval to reach 400 feet)


        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        return send_file(img, mimetype='image/png')

    except Exception as e:
        return {"error":'An error occurred'},500
    finally:
        if conn is not None:
            conn.close()



@app.route('/api/optimize/heatmap/<selectedBatter>/<batterSide>/<selectedPitcher>/<pitcherSide>')
def get_heatmap_optimized(selectedBatter, batterSide, selectedPitcher, pitcherSide):
    try:
        global df_pitcher
        global df_batter

        df_optimized = pd.concat([df_pitcher,df_batter])
        # limit = len(df_optimized) * .1
        # conn = ps.connect(host = "172.18.50.2",
        #         database = "all_games",
        #         user = "postgres",
        #         password = "[AjayPagan12!]")
        # cur = conn.cursor()
        # query = "SELECT * FROM allgames WHERE (batterside = '{batterSide}' AND pitcherthrows='{pitcherSide}) ORDER BY RANDOM() LIMIT {limit} ".format(batterSide=batterSide, pitcherSide=pitcherSide, limit=limit)
        
        # cur.execute(query)
        # result = cur.fetchall()
        # column_names = [desc[0] for desc in cur.description]
        # df = pd.DataFrame(result, columns=column_names)
        # df_optimized = pd.concat([df_optimized, df])
       
        #NOW ONTO THE HEATMAP CREATION
        # Set up plot with baseball field dimensions
        plt.figure(figsize=(10, 8))
        # Plot the heatmap for all hits first
        sns.kdeplot(x=df_optimized['x'], y=df_optimized['y'], cmap='Reds', fill=True, thresh=0.05, alpha=0.8)
        plt.title('Optimized Defensive Heatmap for {selectedPitcher} vs {selectedBatter}'.format(selectedPitcher=selectedPitcher,selectedBatter=selectedBatter)) # this needs to change (the name at least)

        # Set the original limits for the baseball field dimensions
        plt.xlim(-100, 100)
        plt.ylim(-10, 425)

        # Plot the bases as black squares with real-world coordinates
        plt.scatter(0, 0, color='black', s=100, label="Home Plate")
        plt.scatter(45, 60.5, color='black', s=100, label="First Base")
        plt.scatter(0, 127.28, color='black', s=100, label="Second Base")
        plt.scatter(-45, 60.5, color='black', s=100, label="Third Base")

        # Draw lines between the bases to complete the field
        plt.plot([0, 45], [0, 60.5], color='black')
        plt.plot([45, 0], [60.5, 127.28], color='black')
        plt.plot([0, -45], [127.28, 60.5], color='black')
        plt.plot([-45, 0], [60.5, 0], color='black')

        plt.plot([0, 100], [0, 140], color='red', linestyle='--', label="Foul Line (1st Base Side)")
        plt.plot([0, -100], [0, 140], color='red', linestyle='--', label="Foul Line (3rd Base Side)")
        # Draw a dotted ring for the infield (expand the oval to reach 400 feet)


        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        return send_file(img, mimetype='image/png')

    except Exception as e:
        return {"error":'An error occurred'},500
    finally:
        if conn is not None:
            conn.close()

@app.route('/test',methods=['GET'])
def get_test():
    return 'The backend is working'

if __name__ == '__main__':
    app.run(host="localhost", port=8080, debug=True)