import json
import re
import os
import calendar
from pathlib import Path

import pandas as pd
from dash import Dash, dcc, html, Input, Output
import plotly.express as px

with open(os.path.join(Path(__file__).parent, 'data', 'areas.json')) as areas_file:
    areas = json.load(areas_file)
with open(os.path.join(Path(__file__).parent, '.mapbox_token')) as token_file:
    token = token_file.read()

df = pd.read_csv(os.path.join(Path(__file__).parent, 'data', 'count_data.csv'), index_col=0)
months = calendar.month_abbr[1:]

app = Dash(__name__)

app.layout = html.Div(
    id="app-container",
    children=[
        html.Div(
            id="sidebar-container",
            children=[
                html.H1("Squamish Monthly Bird Count"),
                dcc.Tabs(
                    id="tabs",
                    value="tab-map",
                    children=[
                        dcc.Tab(label="Map", value="tab-map"),
                        dcc.Tab(label="Graph", value="tab-graph"),
                    ],
                ),
                html.Div([
                    html.P("Select Species:"),
                    dcc.Dropdown(
                        id="species-dropdown",
                        options=sorted(df["species"].unique()),
                        value="Total Species Count",
                        clearable=False,
                    ),
                    html.P("Selection Line Shape:"),
                    dcc.RadioItems(
                        ['linear', 'spline'],
                        'spline',
                        id='line-shape-radio',
                        inline=True
                    ),
                ])
            ],
        ),
        html.Div(
            id="content-container",
        ),
    ],
)

@app.callback(
    Output('content-container', 'children'),
    Input('tabs', 'value')
)
def render_content_container(tab):
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

@app.callback(
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

@app.callback(
    Output("count-graph", "figure"), 
    Input("species-dropdown", "value"),
    Input("line-shape-radio", "value"),
)
def update_graph(species, line_shape):
    dff = df[(df['species']== species) & (df['id']=='ALL')]

    fig = px.line(dff,
        x='month',
        y='count',
        category_orders= {'month': months},
        color="year",
        color_discrete_sequence=px.colors.qualitative.Light24,
        template="plotly_dark",
        markers=True,
        line_shape=line_shape,

    )

    fig.update_layout(
        margin={"r": 20, "t": 20, "l": 20, "b": 20},
    )

    return fig


if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port='8050')