import json
import os
import calendar
from pathlib import Path

import numpy as np
import pandas as pd
from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go

with open(os.path.join(Path(__file__).parent, 'data', 'areas.json')) as areas_file:
    areas = json.load(areas_file)
with open(os.path.join(Path(__file__).parent, '.mapbox_token')) as token_file:
    token = token_file.read()

df = pd.read_csv(os.path.join(Path(__file__).parent, 'data', 'count_data.csv'), index_col=0)
months = calendar.month_abbr[1:]

# Helper functions
# Stats for df
def get_stats_df(df):
    stats_df = df[df['id']=='ALL']
    stats_df = stats_df.groupby(
        ['month', 'species']
        ).agg(
            mean=('count', np.mean),
            median=('count', np.median),
            std=('count', np.std),
            min=('count', np.min),
            max=('count', np.max)
        ).reset_index()

    stats_df['month'] = pd.Categorical(stats_df['month'], months)
    stats_df = stats_df.sort_values(['month','species']).reset_index(drop=True)
    
    return stats_df

dash_app = Dash(__name__)
app = dash_app.server

dash_app.layout = html.Div(
    id="dash_app-container",
    children=[
        html.Div(
            id="sidebar-container",
            children=[
                html.H1("Squamish Monthly Bird Count"),
                dcc.Tabs(
                    id="tabs",
                    value="tab-graph",
                    children=[
                        dcc.Tab(label="Graph", value="tab-graph"),
                        dcc.Tab(label="Map", value="tab-map"),
                    ],
                ),
                html.P("Select Species:"),
                        dcc.Dropdown(
                            id="species-dropdown",
                            options=sorted(df["species"].unique()),
                            value="Total Species Count",
                            clearable=False,
                        ),
                html.Div(
                    id='sidebar-content',
                    ),
            ],
        ),
        html.Div(
            id="content-container",
        ),
    ],
)

@dash_app.callback(
    Output('sidebar-content', 'children'),
    Input('tabs', 'value')
)
def render_sidebar_content(tab):
    if tab == 'tab-map':
        return []
    elif tab == 'tab-graph':
        return [
            # html.P("Line Shape:"),
            dcc.RadioItems(
                ['spline', 'linear',],
                'spline',
                id='line-shape-radio',
                inline=True
            ),
            dcc.Checklist(
                ['Average', 'Standard Deviation'],
                [],
                id='average-checklist'
            )
        ]


@dash_app.callback(
    Output('content-container', 'children'),
    Input('tabs', 'value')
)
def render_content(tab):
    if tab == 'tab-map':
        return dcc.Graph(
            id="count-map",
            config=dict(responsive=True),
        )
    elif tab == 'tab-graph':
        return dcc.Graph(
            id="count-graph",
            config=dict(responsive=True),
        )

@dash_app.callback(
    Output("count-map", "figure"), 
    Input("species-dropdown", "value")
)
def update_map(species):
    dff = df[df["species"] == species]
    
    fig = px.choropleth_mapbox(
        dff,
        geojson=areas,
        locations="id",
        featureidkey="properties.id",
        color="count",
        color_continuous_scale="Purples",
        range_color=(0, dff["count"].max()),
        zoom=12.5,
        center={"lat": 49.7, "lon": -123.15},
        opacity=0.5,
        labels={"count": "Count", "id": "Area"},
        animation_frame="date",
        template="plotly_dark",
    )
    fig.update_layout(
        margin={"r": 20, "t": 20, "l": 20, "b": 20},
        mapbox_accesstoken=token,
        mapbox_style="satellite-streets",
    )
    if fig["layout"]["updatemenus"]:
        fig["layout"]["updatemenus"][0]["pad"] = dict(r=20, t=25)
        fig["layout"]["sliders"][0]["pad"] = dict(r=0, t=0, b=20)

    return fig

@dash_app.callback(
    Output("count-graph", "figure"), 
    Input("species-dropdown", "value"),
    Input("line-shape-radio", "value"),
    Input('average-checklist', 'value'),
)
def update_graph(species, line_shape, average_checklist):
    dff = df[(df['species']== species) & (df['id']=='ALL')]
    stats_df = get_stats_df(dff)

    fig = px.line(
        dff,
        x='month',
        y='count',
        category_orders= {'month': months},
        color="year",
        color_discrete_sequence=px.colors.qualitative.Light24,
        template="plotly_dark",
        markers=True,
        line_shape=line_shape,
    )

    if 'Average' in average_checklist:
        # Average
        fig.add_trace(
            go.Scatter(
                x=stats_df['month'],
                y=stats_df['mean'], 
                mode="lines",
                line_shape=line_shape,
                name='Average',
                line={'width':4, 'color':'white'},
                showlegend=False
            )
        )
    
    if 'Standard Deviation' in average_checklist:
        # Standard deviation line
        average_plus_std = list(stats_df['mean']+stats_df['std'])
        average_minus_std = list(stats_df['mean']-stats_df['std'])
        rev_average_minus_std = average_minus_std[::-1]
        rev_average_minus_std = [x if x > 0 else 0 for x in rev_average_minus_std]

        fig.add_trace(
            go.Scatter(
                x=months+months[::-1],
                y=average_plus_std+rev_average_minus_std,
                fill='toself',
                fillcolor='rgba(255,255,255,0.3)',
                line_color='rgba(255,255,255,0)',
                mode="lines",
                line_shape=line_shape,
                name='Standard Deviation',
                line={'width':4, 'color':'white'},
                showlegend=False
            )
        )

    fig.update_layout(
        margin={"r": 20, "t": 20, "l": 20, "b": 20},
    )

    fig.data = fig.data[::-1]
    return fig


if __name__ == "__main__":
    dash_app.run_server()