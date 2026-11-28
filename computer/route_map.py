from html import escape
import tempfile
import webbrowser
from pathlib import Path

import folium
from geo import Point


def create_location_map(
    location_nodes: list[Point],
    project_route: list[Point] | None = None,
    waypoints: list[Point] | None = None,
    stats: dict[str, str] | None = None,
) -> Path:
    if not location_nodes:
        raise ValueError("Cannot create a route map without recorded locations.")

    coordinates = [[lat, lon] for lon, lat in location_nodes]
    project_coordinates = [
        [lat, lon] for lon, lat in (project_route or [])
    ]
    waypoint_coordinates = [[lat, lon] for lon, lat in (waypoints or [])]
    location_map = folium.Map(
        location=coordinates[0],
        zoom_start=15,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    if len(project_coordinates) > 1:
        folium.PolyLine(
            project_coordinates,
            color="white",
            weight=11,
            opacity=0.9,
            smooth_factor=0,
            interactive=False,
        ).add_to(location_map)
        folium.PolyLine(
            project_coordinates,
            color="#2469c8",
            weight=7,
            opacity=0.95,
            smooth_factor=0,
            tooltip="Project route",
        ).add_to(location_map)

    if len(coordinates) > 1:
        folium.PolyLine(
            coordinates,
            color="white",
            weight=9,
            opacity=0.9,
            smooth_factor=0,
            interactive=False,
        ).add_to(location_map)
        folium.PolyLine(
            coordinates,
            color="#ec7d22",
            weight=5,
            opacity=0.95,
            smooth_factor=0,
            tooltip="Path taken",
        ).add_to(location_map)

    for index, coordinate in enumerate(waypoint_coordinates, start=1):
        folium.Marker(
            location=coordinate,
            tooltip=f"Waypoint {index}",
            icon=folium.DivIcon(
                icon_size=(26, 26),
                icon_anchor=(13, 13),
                class_name="geoquest-waypoint",
                html=(
                    '<div style="width:22px;height:22px;border-radius:50%;'
                    'background:#ffd43b;border:2px solid white;'
                    'color:#263238;text-align:center;line-height:22px;'
                    f'font: bold 12px Arial,sans-serif">{index}</div>'
                ),
            ),
        ).add_to(location_map)

    folium.Marker(coordinates[0], tooltip="Start", icon=folium.Icon(color="green")).add_to(
        location_map
    )
    folium.Marker(coordinates[-1], tooltip="Finish", icon=folium.Icon(color="red")).add_to(
        location_map
    )

    all_coordinates = coordinates + project_coordinates + waypoint_coordinates
    if len(all_coordinates) > 1:
        location_map.fit_bounds(all_coordinates)

    legend_rows = (
        '<div style="display:flex;align-items:center;gap:8px;margin:5px 0">'
        '<span style="display:inline-block;width:24px;height:4px;background:#2469c8"></span>'
        '<span>Project route</span></div>'
        '<div style="display:flex;align-items:center;gap:8px;margin:5px 0">'
        '<span style="display:inline-block;width:24px;height:4px;background:#ec7d22"></span>'
        '<span>Path taken</span></div>'
        '<div style="display:flex;align-items:center;gap:8px;margin:5px 0">'
        '<span style="display:inline-block;width:14px;height:14px;border-radius:50%;'
        'background:#ffd43b;border:2px solid white"></span><span>Waypoint</span></div>'
    )
    stats_rows = ""
    if stats:
        stats_rows = '<div style="border-top:1px solid #53616d;margin-top:8px;padding-top:6px">'
        for label, value in stats.items():
            stats_rows += (
                '<div style="display:flex;justify-content:space-between;gap:18px;margin:4px 0">'
                f'<span>{escape(label)}</span><strong>{escape(value)}</strong></div>'
            )
        stats_rows += "</div>"

    legend = folium.Element(
        '<div style="position:fixed;left:12px;bottom:28px;z-index:9999;'
        'min-width:190px;padding:10px 13px;border-radius:8px;'
        'background:rgba(37,49,60,.94);color:white;'
        'box-shadow:0 2px 10px rgba(0,0,0,.3);'
        'font:12px Arial,sans-serif">'
        '<div style="font-size:13px;font-weight:bold;margin-bottom:5px">GeoQuest</div>'
        f"{legend_rows}{stats_rows}</div>"
    )
    location_map.get_root().html.add_child(legend)

    with tempfile.NamedTemporaryFile(prefix="geoquest-", suffix=".html", delete=False) as file:
        map_path = Path(file.name)
    location_map.save(str(map_path))
    return map_path


def open_location_map(map_path: Path | None) -> bool:
    if map_path is None:
        return False

    if webbrowser.open(map_path.as_uri()):
        return True

    print("Error: Could not open location map in browser.")
    return False
