## IMPORTS

import requests
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import plotly.express as px

## IMPORT AND CLEAN DATA

# API Info

my_key = '1F96B5737FB4FF22A1F6D3B1A91FBF16'
my_id = '76561198870952934'
url_get_owned_games = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001"
url_get_player_achievements = "http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001"

# Get info for owned games

owned_games_res = requests.get(url_get_owned_games, 
                               params={'key': my_key, 
                                       'steamid': my_id, 
                                       'include_appinfo': 1, 
                                       'include_played_free_games': 1})

owned_games_json = owned_games_res.json()

# Create dictionary of games and their ids

game_ids = {owned_games_json['response']['games'][n]['name']: owned_games_json['response']['games'][n]['appid'] \
           for n in range(0, owned_games_json['response']['game_count'])}

# Get info for player achievements

def get_achievements(game_id):
    user_achievements_res = requests.get(
        url_get_player_achievements, 
        params={'appid': game_id,
                'key': my_key, 
                'steamid': my_id})
    return user_achievements_res.json()

all_achievements = {k: get_achievements(v) for k, v in game_ids.items()}

# Other functions (get_achievements_available, get_num_achieved, get_pct_achieved)

def get_achievements_available(game):
    try:
        a = len(all_achievements[game]['playerstats']['achievements'])
    except:
        a = None
    return a

def get_num_achieved(game):
    total_achieved = 0
    try:
        for a in range(len(all_achievements[game]['playerstats']['achievements'])):
            total_achieved += all_achievements[game]['playerstats']['achievements'][a]['achieved']
    except:
        total_achieved = None
    return total_achieved

def get_pct_achieved(game):
    try:
        pct = round(get_num_achieved(game)/get_achievements_available(game), 3)*100
    except:
        pct = None
    return pct

# Convert UNIX time in player achievements to UTC datetime

def convert_time(time):
    """Converts UNIX time to UTC datetime"""
    convert = datetime.fromtimestamp(time).strftime('%Y-%m-%d')
    return datetime.strptime(convert,'%Y-%m-%d')

## CREAT DFs

# Create achievements df

def create_game_achievements_df(game):
    """Creates a dataframe where each row is an achievement available in the game entered"""
    try:
        df = pd.DataFrame(all_achievements[game]['playerstats']['achievements'])
        df['game_id'] = game_ids[game]
        df['game'] = game
        df.rename(columns = {'apiname': 'achievement_name'}, inplace=True)
        df['unlockdate_fmt'] = pd.to_datetime(df['unlocktime'].apply(convert_time))
        df = df[['game_id', 'game', 'achievement_name', 'achieved', 'unlocktime', 'unlockdate_fmt']]
        return df
    except:
        pass

all_achievements_df = pd.DataFrame(columns = ['game_id', 
                                              'game', 
                                              'achievement_name', 
                                              'achieved', 
                                              'unlocktime',
                                              'unlockdate_fmt'
                                             ])

for g in game_ids.keys():
    df_g = create_game_achievements_df(g)
    all_achievements_df = pd.concat([all_achievements_df, df_g])

# Make dictionary & df for games & their playtimes

game_playtimes_hours = {owned_games_json['response']['games'][n]['name']: round(owned_games_json['response']['games'][n]['playtime_forever']/60) \
           for n in range(0, owned_games_json['response']['game_count'])}

df_playtimes = pd.DataFrame({'game': game_playtimes_hours.keys(),
                   "hours_played": game_playtimes_hours.values()
                  })

# Clean df_playtimes

df_playtimes['game'].replace({"PLAYERUNKNOWN'S BATTLEGROUNDS": 'PUBG',
                    "Command & Conquer™ Remastered Collection": 'Command & Conquer',
                    "Counter-Strike: Global Offensive": 'CS:GO'
                   },
                   inplace=True)

df_playtimes.drop(df_playtimes.loc[df_playtimes['hours_played']==0].index, inplace=True)

df_playtimes_sorted = df_playtimes.sort_values('hours_played', ascending=False)

# Create top stats df

def get_top_stats(game):
    game_dict = { 
        'game_id': game_ids[game], 
        'game': game,
        'hours_played': game_playtimes_hours[game], 
        'achievements_available': get_achievements_available(game), 
        'achievements_achieved': get_num_achieved(game),
        'pct_achievements_achieved': get_pct_achieved(game)
    }
    return game_dict

list_top_stat_dicts = [get_top_stats(g) for g in game_ids.keys()]

df_top_stats = pd.DataFrame(list_top_stat_dicts)
df_top_stats['game'].replace({"PLAYERUNKNOWN'S BATTLEGROUNDS": 'PUBG',
                    "Command & Conquer™ Remastered Collection": 'Command & Conquer',
                    "Counter-Strike: Global Offensive": 'CS:GO'
                   },
                   inplace=True)
df_top_stats.drop(df_top_stats.loc[df_top_stats['hours_played']==0].index, inplace=True)
df_top_stats = df_top_stats[df_top_stats['pct_achievements_achieved'].notna()]

# Create alphabetical list of games for dropdown in app

game_dropdown_list = sorted([g for g in df_playtimes['game']])
game_dropdown_list_dict = [{'label': g, 'value': g} for g in game_dropdown_list]

## Layout 

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([

    html.H1('Steam Game Dashboard', style={'text-align': 'center'}),

    html.Div('''
        Dashboard for my owned game stats (source: Steam API)
    '''),

    dcc.Dropdown(
        id='my-dropdown',
        options=game_dropdown_list_dict,
        multi=True,
        value=game_dropdown_list,
        placeholder='Select game(s).',
        clearable=True
    ),

    html.H6('Total playtime (hours) per game', style={'text-align': 'center'}),

    html.Div([

        dcc.Graph(
            id='hours_played_bar', 
            figure={},
            config={'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'autoScale2d',
                                                'resetScale2d','toggleHover', 'zoom2d',
                                                'toggleSpikelines', 'hoverCompareCartesian']}
            )
    ]),

    html.H6 ('Playtime (hours) vs Achievement Percentage', style={'text-align': 'center'}),

    html.Div([
        dcc.Graph(
            id='hours_achieve_pct_scatter', 
            figure={},
            config={'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'autoScale2d',
                                                'resetScale2d','toggleHover', 'zoom2d',
                                                'toggleSpikelines', 'hoverCompareCartesian']}
            )
    ])
    
], style={'marginLeft': 100, 'marginRight': 100})

## Callback to tie dropdown to hours_played_bar

@app.callback(
        Output(component_id='hours_played_bar', component_property='figure'),
        [Input(component_id='my-dropdown', component_property='value')]
)

def update_hours_played_bar(options_selected):

    df_init = df_playtimes_sorted.copy()
    df_graph = pd.DataFrame(columns = list(df_init.columns))
    
    for i in options_selected:
        df_i = df_init[df_init['game'] == i]
        df_graph = pd.concat([df_graph, df_i])
    
    # Bar chart
    fig = px.bar(
        df_graph, 
        x="game", 
        y="hours_played", 
        barmode="group", 
        text="hours_played"
        )

    # Additional formatting for bar chart
    fig.update_traces(textposition='outside')
    fig.update_layout(margin=dict(l=50, r=50, t=10, b=50))
    fig.update_xaxes(categoryorder="total descending")

    return fig

## Callback to tie dropdown to hours_achieve_pct_scatter

@app.callback(
        Output(component_id='hours_achieve_pct_scatter', component_property='figure'),
        [Input(component_id='my-dropdown', component_property='value')]
)

def update_scatter(options_selected):
    
    df_init = df_top_stats.copy()
    df_graph = pd.DataFrame(columns = list(df_init.columns))

    for i in options_selected:
        df_i = df_init[df_init['game'] == i]
        df_graph = pd.concat([df_graph, df_i])

    fig = px.scatter(
        df_graph,
        x="pct_achievements_achieved",
        y="hours_played",
        size="pct_achievements_achieved",
        hover_data=['hours_played','pct_achievements_achieved','game']
        )

    return fig

if __name__ == '__main__':
    app.run_server(debug=True)