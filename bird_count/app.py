import json
import os
import calendar
from pathlib import Path

import numpy as np
import pandas as pd
from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template

# loads the "sketchy" template and sets it as the default
load_figure_template("darkly")
dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"
dash_app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY, dbc_css])
app = dash_app.server

with open(os.path.join(Path(__file__).parent, "data", "areas.json")) as areas_file:
    areas = json.load(areas_file)
with open(os.path.join(Path(__file__).parent, ".mapbox_token")) as token_file:
    token = token_file.read()

df = pd.read_csv(
    os.path.join(Path(__file__).parent, "data", "count_data.csv"), index_col=0
)
months = calendar.month_abbr[1:]

# Helper functions
# Stats for df
def get_stats_df(df):
    stats_df = df[df["id"] == "ALL"]
    stats_df = (
        stats_df.groupby(["month", "species"])
        .agg(
            mean=("count", np.mean),
            median=("count", np.median),
            std=("count", np.std),
            min=("count", np.min),
            max=("count", np.max),
        )
        .reset_index()
    )

    stats_df["month"] = pd.Categorical(stats_df["month"], months)
    stats_df = stats_df.sort_values(["month", "species"]).reset_index(drop=True)

    return stats_df

# Create list of colours for line chart
def colour_array(size):
    return [f"rgb({x}, {x}, 255)" for x in np.linspace(255, 0, size, dtype=int)]

# Layout
dash_app.layout = dbc.Container(
    id="dash_app-container",
    fluid=True,
    className="dbc",
    style={"height": "100vh"},
    children=[
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        id="sidebar-container",
                        children=[
                            html.H1("Squamish Monthly Bird Count"),
                            html.Br(),
                            html.P("Select Species:"),
                            dcc.Dropdown(
                                id="species-dropdown",
                                options=sorted(df["species"].unique()),
                                value="Total Species Count",
                                clearable=False,
                            ),
                            html.P("Date Range:"),
                            html.P(
                                dcc.RangeSlider(
                                    min=df["year"].min(),
                                    max=df["year"].max(),
                                    step=1,
                                    marks=None,
                                    tooltip={
                                        "placement": "bottom",
                                        "always_visible": True,
                                    },
                                    id="year-range-slider",
                                ),
                            ),
                            # html.P(),
                            dcc.Tabs(
                                id="tabs",
                                value="tab-graph",
                                children=[
                                    dcc.Tab(
                                        label="Graph",
                                        value="tab-graph",
                                    ),
                                    dcc.Tab(
                                        label="Map",
                                        value="tab-map",
                                    ),
                                ],
                            ),
                            html.Div(
                                id="sidebar-content"
                            )
                        ],
                    ),
                    width=2,
                    style={"height": "100%"}
                ),
                dbc.Col(
                    html.Div(
                        id="content-container",
                        style={"height": "100vh"}
                    ),
                    width=10,
                    style={"height": "100%"}
                ),
            ],
            # align='stretch',
            style={"height": "100vh"},
        )
    ],
)



@dash_app.callback(
    Output("sidebar-content", "children"), 
    Input("tabs", "value")
)
def render_sidebar_content(tab):
    if tab == "tab-map":
        return []
    elif tab == "tab-graph":
        return [
            # html.P("Line Shape:"),
            dcc.RadioItems(
                [
                    "spline",
                    "linear",
                ],
                "spline",
                id="line-shape-radio",
                inline=True,
            ),
            dcc.Checklist(
                ["Average", "Standard Deviation"], [], id="average-checklist"
            ),
        ]


@dash_app.callback(
    Output("content-container", "children"), 
    Input("tabs", "value")
)
def render_content(tab):
    if tab == "tab-map":
        return dcc.Graph(
            id="count-map",
            config=dict(responsive=True),
            style={"height": "100vh"}
        )
    elif tab == "tab-graph":
        return dcc.Graph(
            id="count-graph",
            config=dict(responsive=True),
            style={"height": "100vh"}
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
        # template="plotly_dark",
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
    Input("year-range-slider", "value"),
    Input("species-dropdown", "value"),
    Input("line-shape-radio", "value"),
    Input("average-checklist", "value"),
)
def update_graph(year_range, species, line_shape, average_checklist):
    dff = df[(df["species"] == species) & (df["id"] == "ALL")]
    if year_range is not None:
        dff = dff[(dff["year"] >= year_range[0]) & (dff["year"] <= year_range[1])]
    stats_df = get_stats_df(dff)

    fig = px.line(
        dff,
        x="month",
        y="count",
        category_orders={"month": months},
        color="year",
        color_discrete_sequence=colour_array(len(dff["year"].unique())),
        # color_discrete_sequence=px.colors.qualitative.Light24,
        # template="plotly_dark",
        markers=True,
        line_shape=line_shape,
        labels={"year": "Year", "month": "Month", "count": "Count"},
    )

    # Average
    if "Average" in average_checklist:
        fig.add_trace(
            go.Scatter(
                x=stats_df["month"],
                y=stats_df["mean"],
                mode="lines",
                line_shape=line_shape,
                name="Average",
                line={"width": 4, "color": "Red"},
                showlegend=False,
            )
        )

    # Standard deviation line
    if "Standard Deviation" in average_checklist:
        average_plus_std = list(stats_df["mean"] + stats_df["std"])
        average_minus_std = list(stats_df["mean"] - stats_df["std"])
        rev_average_minus_std = average_minus_std[::-1]
        rev_average_minus_std = [x if x > 0 else 0 for x in rev_average_minus_std]

        fig.add_trace(
            go.Scatter(
                x=months + months[::-1],
                y=average_plus_std + rev_average_minus_std,
                fill="toself",
                fillcolor="rgba(255,255,255,0.3)",
                line_color="rgba(255,255,255,0)",
                mode="lines",
                line_shape=line_shape,
                name="Standard Deviation",
                line={"width": 4, "color": "white"},
                showlegend=False,
            )
        )

    fig.update_layout(
        margin={"r": 20, "t": 20, "l": 20, "b": 20},
        xaxis={
            "title": "",
            "visible": True,
            "showticklabels": True,
            "range": [-0.1, 11.1],
        },
        yaxis={"title": "Count", "visible": True},
    )

    return fig


if __name__ == "__main__":
    dash_app.run_server()
