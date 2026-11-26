import tempfile
import webbrowser
from pathlib import Path

import folium
from geo import Point


def create_location_map(location_nodes: list[Point]) -> Path:
    coordinates = [[lat, lon] for lon, lat in location_nodes]
    location_map = folium.Map(location=coordinates[0], zoom_start=15)

    if len(coordinates) > 1:
        folium.PolyLine(
            coordinates,
            color="blue",
            weight=7,
            opacity=0.9,
            smooth_factor=0,
            tooltip="Path taken",
        ).add_to(location_map)
        location_map.fit_bounds(coordinates)

    for index, coordinate in enumerate(coordinates, start=1):
        folium.CircleMarker(
            location=coordinate,
            radius=4,
            color="blue",
            fill=True,
            fill_opacity=0.8,
            popup=f"Location {index}",
        ).add_to(location_map)

    folium.Marker(coordinates[0], tooltip="Start", icon=folium.Icon(color="green")).add_to(
        location_map
    )
    folium.Marker(coordinates[-1], tooltip="Finish", icon=folium.Icon(color="red")).add_to(
        location_map
    )

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
