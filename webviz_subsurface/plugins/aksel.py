from uuid import uuid4
from pathlib import Path
from typing import List
import dash
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from matplotlib.colors import ListedColormap
import xtgeo
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_subsurface_components import LayeredMap
from webviz_config import WebvizPluginABC
from webviz_config.webviz_store import webvizstore
from webviz_config.utils import calculate_slider_step

from .._datainput.well import load_well
from .._datainput.surface import make_surface_layer, get_surface_fence


class HorizonUncertaintyViewer(WebvizPluginABC):
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
    """
This plugin visualizes surfaces in a map view and seismic in a cross section view.
The cross section is defined by a polyline interactively edited in the map view.
* `surfacefiles`: List of file paths to Irap Binary surfaces
* `surfacenames`: Corresponding list of displayed surface names
* `zunit`: z-unit for display
* `colors`: List of colors to use
"""

    ### Initialize ###
    def __init__(
        self,
        app,
        surfacefiles: List[Path],
        surfacefiles_de: List[Path],
        wellfiles: List[Path],
        surfacenames: list = None,
        wellnames: list = None,
        zunit="depth (m)",
    ):

        super().__init__()
        self.zunit = zunit
        self.surfacefiles = [str(surffile) for surffile in surfacefiles]
        self.surfacefiles_de = [str(surfacefile_de) for surfacefile_de in surfacefiles_de]
        if surfacenames is not None:
            if len(surfacenames) != len(surfacefiles):
                raise ValueError(
                    "List of surface names specified should be same length as list of surfacefiles"
                )
            self.surfacenames = surfacenames
        else:
            self.surfacenames = [Path(surfacefile).stem for surfacefile in surfacefiles]
        
        self.wellfiles = [str(wellfile) for wellfile in wellfiles]
        if wellnames is not None:
            if len(wellnames) != len(wellfiles):
                raise ValueError(
                    "List of surface names specified should be same length as list of surfacefiles"
                )
            self.wellnames = wellnames
        else:
            self.wellnames = [Path(wellfile).stem for wellfile in wellfiles]
        self.plotly_theme = app.webviz_settings["theme"].plotly_theme
        self.uid = uuid4()
        self.set_callbacks(app)

    ### Generate unique ID's ###
    def ids(self, element):
        return f"{element}-id-{self.uid}"

    ### Layout map section ###
    @property
    def map_layout(self):
        return None

    ### Layout cross section ###
    @property
    def cross_section_layout(self):
        return html.Div(
            children=[
                wcc.FlexBox(
                    children=[
                        html.Div(
                            children=[
                                html.Label(
                                    style={
                                        "font-weight": "bold",
                                        "textAlign": "center",
                                    },
                                    children="Select well",
                                ),
                                dcc.Dropdown(
                                    id=self.ids("well"),
                                    options=[
                                        {"label": name, "value": path}
                                        for name, path in zip(
                                            self.wellnames, self.wellfiles
                                        )
                                    ],
                                    value=self.wellfiles[0],
                                    clearable=False,
                                ),
                            ]
                        ),
                    ],
                ),
                wcc.FlexBox(
                    children=[
                        html.Div(
                            children=[
                                html.Label(
                                    style={
                                        "font-weight": "bold",
                                        "textAlign": "center",
                                    },
                                    children="Graph Settings",
                                ),
                                dcc.Checklist(
                                    id=self.ids('all-surfaces-checkbox'),
                                    options=[{'label': 'all', 'value': 'all'}],
                                    value=['all'],
                                ),
                                dcc.Checklist(
                                    id=self.ids('surfaces-checklist'),
                                    options=[{'label': k, 'value': k} for k in self.surfacenames],
                                    value=self.surfacenames,
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    children=[
                        html.Div(
                            style={
                                "marginTop": "20px",
                                "height": "800px",
                                "zIndex": -9999,
                            },
                            children=wcc.Graph(
                                figure={"displayModeBar": True}, id=self.ids("cross-section-view")
                            ),
                        )
                    ]
                ),
            ]
        )

    ### Flexbox ###
    @property
    def layout(self):
        return wcc.FlexBox(
            id=self.ids("layout"),
            children=[
                html.Div(style={"flex": 1}, children=self.map_layout),
                html.Div(style={"flex": 1}, children=self.cross_section_layout),
            ],
        )


    def set_callbacks(self, app):
        ### Callbacks for updating cross-section-view ###
        @app.callback(
            Output(self.ids("cross-section-view"), "figure"),
            [
                Input(self.ids("well"), "value")
            ],
        )
        def _render_surface(wellpath):
            well = xtgeo.Well(get_path(wellpath))
            return make_gofig(well, self.surfacefiles, self.surfacefiles_de)
        
        ### Callback for update of tickboxes in cross-section-view
        @app.callback(
            Output(self.ids("surfaces-checklist"), "value"),
            [Input(self.ids("all-surfaces-checkbox"), "value")],
        )
        def update_surface_tickboxes(all_surfaces_checkbox):
            return self.surfacenames if all_surfaces_checkbox == ['all'] else []

    def add_webvizstore(self):
        return [(get_path, [{"path": fn}]) for fn in self.surfacefiles]

@webvizstore
def get_path(path) -> Path:
    return Path(path)

def make_gofig(well, surfacefiles, surfacefiles_de):
    # Generate a polyline along a well path
    well_fence = well.get_fence_polyline(nextend=0, sampling=5)
    # Get surface values along the polyline
    well.create_relative_hlen()
    df = well.dataframe
    surfaces=[]
    surfaces_de = []
    surf_lines = []
    surf_lines_de = []
    for path in surfacefiles:
        surfaces.append(xtgeo.surface_from_file(path, fformat="irap_binary"))
    for path in surfacefiles_de:
        surfaces_de.append(xtgeo.surface_from_file(path, fformat="irap_binary"))
    for sfc in surfaces_de:
        surf_lines_de.append(sfc.get_randomline(well_fence))
    for sfc in surfaces:
        surf_lines.append(sfc.get_randomline(well_fence))
    
    layout = {}
    layout.update(
        {          
            "yaxis": {
                "title": "Depth (m)",
                "autorange": "reversed",
            },
            "xaxis": {
                "title": "Distance along polyline",
            },
            "plot_bgcolor":'rgb(233,233,233)'
        }
    )

    data = [{"type": "line",
                "y": surf_line[:,1],
                "x": surf_line[:,0],
                "name": "surface",
                "fill":"tonexty"
             }
            for surf_line in surf_lines
            ]

    data.extend([{"type": "line",
                "y": surf_line_de[:,1],
                "x": surf_line_de[:,0],
                "name": "depth error",
                "fill":"tonexty"
             }
            for surf_line_de in surf_lines_de
            ])
    
    data.append({
                "type": "line",
                "y": df["Z_TVDSS"],
                "x": df["R_HLEN"],
                "name": "well"
                })
    return {'data':data,
            'layout':layout}