from flask import Flask, request
import users
import dash
import dash_bootstrap_components as dbc
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import plotly.express as px
from influx_helper import influxHelper
import main_html


server = Flask(__name__)
# Load configurations
server.config.from_object('default_settings')
server.config.from_envvar('PLANTBUDDY_SETTINGS')

# Dashboard is built using plotly's dash package. This also includes bootstap styles from dash_bootstrap
app = app = dash.Dash(__name__, server=server, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

cloud_host = server.config['INFLUXDB_HOST']
cloud_org = server.config['INFLUXDB_ORG']
cloud_bucket = server.config['INFLUXDB_BUCKET']
cloud_token = server.config['INFLUXDB_TOKEN']

graph_default = {"deviceID": "eui-323932326d306512"}


influx = influxHelper(host=cloud_host, org=cloud_org, bucket=cloud_bucket, token=cloud_token)

# Get user. Currently static refrence. Used to filter sensor data in InfluxDB
# TODO change this to login in page. 
user = users.authorize_and_get_user(request)


# This is our html snippets from the main_html file
sidebar = main_html.createNav()
app.layout = main_html.layout(sidebar)


@app.callback(
    Output("tab-content", "children"),
    [Input("tabs", "active_tab"), Input("store", "data")],
)

def render_tab_content(active_tab, data):
    """
    This callback takes the 'active_tab' property as input, as well as the
    stored graphs, and renders the tab content depending on what the value of
    'active_tab' is.
    """
    if active_tab and data is not None:
        if active_tab == "temperature":
            return dbc.Row(
                [
                    dbc.Col( dbc.Card([dcc.Graph(figure=data["soil_temp_graph"])],style={"width": "auto"}), md=6),
                    dbc.Col( dbc.Card([dcc.Graph(figure=data["air_temp_graph"])],style={"width": "auto"}), md=6),
     
                ]
            )
        elif active_tab == "hum_and_moisture":
            return dbc.Row(
                [   
                    dbc.Col( dbc.Card([dcc.Graph(figure=data["humidity_graph"])],style={"width": "auto"}), md=6),
                    dbc.Col( dbc.Card([dcc.Graph(figure=data["soil_moisture"])],style={"width": "auto"}), md=6),
                ]
            )
        elif active_tab == "light":
            return dbc.Row(
                [   
                    dbc.Col( dbc.Card([dcc.Graph(figure=data["light_graph"])],style={"width": "auto"}), md=6),
                ]
            )
    return "No tab selected"


@app.callback(Output("store", "data"), [Input("button", "n_clicks")])
def generate_graphs(n):
# Generate graphs based upon pandas data frame. 
    df = influx.querydata( "soil_temperature", graph_default["deviceID"] )
    soil_temp_graph = px.line(df, x="time", y="soil_temperature", title="Soil Temperature")

    df = influx.querydata( "air_temperature", graph_default["deviceID"] )
    air_temp_graph= px.line(df, x="time", y="air_temperature", title="Air Temperature")

    df = influx.querydata( "humidity", graph_default["deviceID"] )
    humidity_graph= px.line(df, x="time", y="humidity", title="humidity")

    df = influx.querydata( "soil_moisture", graph_default["deviceID"] )
    soil_moisture= px.line(df, x="time", y="soil_moisture", title="Soil Moisture")

    df = influx.querydata( "light", graph_default["deviceID"] )
    light_graph= px.line(df, x="time", y="light", title="light")

    # save figures in a dictionary for sending to the dcc.Store
    return {
            "soil_temp_graph": soil_temp_graph, 
            "air_temp_graph": air_temp_graph, 
            "humidity_graph": humidity_graph, 
            "soil_moisture": soil_moisture,
            "light_graph": light_graph
            }

# Server call used to write sensor data to InfluxDB
# The methods in this function are inside influx_helper.py
@server.route("/write", methods = ['POST'])
def write():
    user = users.authorize_and_get_user(request)
    d = influx.parse_line(request.data.decode("UTF-8"), user["user_name"])
    influx.write_to_influx(d)
    return {'result': "OK"}, 200

@server.route("/notify", methods = ['POST'])
def notify():
    print("notification received", flush=True)
    print(request.data, flush=True)
    return {'result': "OK"}, 200

if __name__ == '__main__':
  app.run_server(host='0.0.0.0', port=5001, debug=True)