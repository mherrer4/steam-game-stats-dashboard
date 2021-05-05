## IMPORTS

import requests
import time
import pandas as pd
import numpy as np
from datetime import datetime

# Dash imports

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.express as px

## CALL AND CLEAN DATA

# API Info

my_key = ### request your own key from Steam ### 
my_id = ### use your Steam Account ID ###

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
    """Returns a dictionary of all achievement info for the game associated with input ID"""
    user_achievements_res = requests.get(
        url_get_player_achievements, 
        params={'appid': game_id,
                'key': my_key, 
                'steamid': my_id})
    return user_achievements_res.json()

all_achievements = {k: get_achievements(v) for k, v in game_ids.items()}

# Other functions (get_achievements_available, get_num_achieved, get_achievement_pct)

def get_achievements_available(game):
    """Returns a count of all available achievements for the inputted game"""
    try:
        a = len(all_achievements[game]['playerstats']['achievements'])
    except:
        a = None
    return a

def get_num_achieved(game):
    """Returns a count of completed achievements for the inputted game"""
    total_achieved = 0
    try:
        for a in range(len(all_achievements[game]['playerstats']['achievements'])):
            total_achieved += all_achievements[game]['playerstats']['achievements'][a]['achieved']
    except:
        total_achieved = None
    return total_achieved

def get_achievement_pct(game):
    """Returns the achievement percentage (# achieved/# available) for the inputted game"""
    try:
        pct = round(get_num_achieved(game)/get_achievements_available(game), 2)*100
    except:
        pct = None
    return pct

# # Create dataframes to be used in dashboard visualizations

# Create dictionary of games and their total playtime hours
game_playtimes_hours = {owned_games_json['response']['games'][n]['name']: round(owned_games_json['response']['games'][n]['playtime_forever']/60) \
           for n in range(0, owned_games_json['response']['game_count'])}

# Turn dictionary into a dataframe
df_playtimes = pd.DataFrame({'game': game_playtimes_hours.keys(),
                   "hours_played": game_playtimes_hours.values()
                  })

# # Clean df_playtimes

# Reduce length of some game names for easier viewing in data visualization
df_playtimes['game'].replace({"PLAYERUNKNOWN'S BATTLEGROUNDS": 'PUBG',
                    "Command & Conquer™ Remastered Collection": 'Command & Conquer',
                    "Counter-Strike: Global Offensive": 'CS:GO'
                   },
                   inplace=True)

# Remove games with zero hours played
df_playtimes.drop(df_playtimes.loc[df_playtimes['hours_played']==0].index, inplace=True)

# # Create top stats df

def get_top_stats(game):
    """Returns dictionary of stats for the inputted game"""
    game_dict = { 
        'game_id': game_ids[game], 
        'game': game,
        'hours_played': game_playtimes_hours[game], 
        'achievements_available': get_achievements_available(game), 
        'achievements_achieved': get_num_achieved(game),
        'achievement_pct': get_achievement_pct(game)
    }
    return game_dict

# Create a list of all game's stats dictionaries
list_top_stat_dicts = [get_top_stats(g) for g in game_ids.keys()]

# Turn list into a dataframe
df_top_stats = pd.DataFrame(list_top_stat_dicts)

# # Clean df_top_stats

# Reduce length of some game names for easier viewing in data visualization
df_top_stats['game'].replace({"PLAYERUNKNOWN'S BATTLEGROUNDS": 'PUBG',
                    "Command & Conquer™ Remastered Collection": 'Command & Conquer',
                    "Counter-Strike: Global Offensive": 'CS:GO'
                   },
                   inplace=True)

# Remove games where achievement percentage is NaN
df_top_stats = df_top_stats[df_top_stats['achievement_pct'].notna()]

# Create alphabetical list of games for dropdown in app (used as "value" in dcc.Dropdown component)
game_dropdown_list = sorted([g for g in df_playtimes['game']])

# Create list of label & values for dropdown options in app (used as "options" in dcc.Dropdown component)
game_dropdown_list_dict = [{'label': g, 'value': g} for g in game_dropdown_list]

# # Dash app Layout 

# Import css stylesheet
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# Define app
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# Describe layout
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

    html.Br(

    ),

    # Define dashboard tabs

    dcc.Tabs(id='my-tabs', value='playtime-tab', children=[

        dcc.Tab(label='Playtime', value='playtime-tab', children=[
            
            # Playtime graph title

            html.H6('Total playtime (hours) per game', style={'text-align': 'center'}),

            # Playtime graph - bar chart

            html.Div([

                dcc.Graph(
                    id='hours_played_bar', 
                    figure={},
                    # Remove some graph toggling options that come with default app, to declutter visual
                    config={'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'autoScale2d',
                                                        'resetScale2d','toggleHover', 'zoom2d',
                                                        'toggleSpikelines', 'hoverCompareCartesian']}
                    )
            ]),
                ]),

        dcc.Tab(label='Achievement %', value='achievement-pct-tab', children=[
            
            # Achievement pct graph title

            html.H6('Achievement percentage per game', style={'text-align': 'center'}),

            # Achievement pct graph - bar chart

            html.Div([

                dcc.Graph(
                    id='achievements_pct_bar', 
                    figure={},
                    # Remove some graph toggling options that come with default app, to declutter visual
                    config={'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'autoScale2d',
                                                        'resetScale2d','toggleHover', 'zoom2d',
                                                        'toggleSpikelines', 'hoverCompareCartesian']}
                    )
            ]),
                ]),

        dcc.Tab(label='Playtime vs Achievements', value='scatter-tab', children=[
            
            # Playtime vs achievements title

            html.H6 ('Playtime (hours) vs Achievement Percentage', style={'text-align': 'center'}),

            # Playtime vs achievements graph - scatterplot

            html.Div([
                dcc.Graph(
                    id='hours_achieve_pct_scatter', 
                    figure={},
                    # Remove some graph toggling options that come with default app, to declutter visual
                    config={'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'autoScale2d',
                                                        'resetScale2d','toggleHover', 'zoom2d',
                                                        'toggleSpikelines', 'hoverCompareCartesian']}
                    )
            ])
        ]),
    ]),

    html.Div(id='tabs-content'),

    # End tabs

], style={'marginLeft': 100, 'marginRight': 100})

# # Tabs callback

@app.callback(Output('tabs-content', 'children'),
              Input('my-tabs', 'value'))

def render_content(tab):
    if tab == 'Playtime':
        return html.Div([
            html.H3('Tab content 1')
        ])
    elif tab == 'Achievements %':
        return html.Div([
            html.H3('Tab content 2')
        ])
    elif tab == 'Playtime vs Achievements':
        return html.Div([
            html.H3('Tab content 3')
        ])

# # Callback to tie dropdown to hours_played_bar visualization

@app.callback(
    Output(component_id='hours_played_bar', component_property='figure'),
    [Input(component_id='my-dropdown', component_property='value')]
)

def update_hours_played_bar(options_selected):

    df_init = df_playtimes.copy()
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

# # Callback to tie dropdown to achievement_pct_bar visual

@app.callback(
        Output(component_id='achievements_pct_bar', component_property='figure'),
        [Input(component_id='my-dropdown', component_property='value')]
)

def update_achievement_pct_bar(options_selected):

    df_init = df_top_stats.copy()
    df_graph = pd.DataFrame(columns = list(df_init.columns))
    
    for i in options_selected:
        df_i = df_init[df_init['game'] == i]
        df_graph = pd.concat([df_graph, df_i])
    
    # Bar chart
    fig = px.bar(
        df_top_stats, 
        x="game", 
        y="achievement_pct", 
        barmode="group",
        text="achievement_pct"
    )

    # Additional formatting for bar chart
    fig.update_traces(textposition='outside')
    fig.update_layout(margin=dict(l=50, r=50, t=10, b=50))
    fig.update_xaxes(categoryorder="total descending")

    return fig

# # Callback to tie dropdown to scatterplot visual

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
        x="achievement_pct",
        y="hours_played",
        size="achievement_pct",
        hover_data=['hours_played','achievement_pct','game'],
        text="game"
        )
    
    fig.update_traces(textposition='top center')

    return fig

if __name__ == '__main__':
    app.run_server(debug=True)