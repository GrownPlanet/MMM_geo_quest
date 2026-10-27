import requests
import geocoder
import folium
import math

mapbox_token = "<redacted>"

def get_location_by_address(address):
    g = geocoder.mapbox(address, key=mapbox_token)
    return f"{g.latlng[1]},{g.latlng[0]}"

def get_current_location():
    g = geocoder.ip("me")
    return f"{g.latlng[1]},{g.latlng[0]}"

def get_route_points(location, destination):
    data = requests.get(f"https://api.mapbox.com/directions/v5/mapbox/walking/{location};{destination}", params={
        "access_token": mapbox_token,
        "geometries": "geojson"
    })

    directions = data.json()

    if directions.get("code") != "Ok":
        print("Mapbox error:", directions)
        return None

    route = directions["routes"][0]

    distance_km = route["distance"] / 1000
    duration_min = route["duration"] / 60
    route_points = route["geometry"]["coordinates"]

    return (
        f"Distance: {distance_km:.2f} km",
        f"Duration: {duration_min:.0f} minutes",
        route_points
    )


def is_bend(p1, p2, p3, threshold=20):
    lat1, lon1 = p1
    lat2, lon2 = p2
    lat3, lon3 = p3

    angle1 = math.atan2(lon2 - lon1, lat2 - lat1)
    angle2 = math.atan2(lon3 - lon2, lat3 - lat2)

    difference = abs(math.degrees(angle2 - angle1))
    difference = min(difference, 360 - difference)

    return difference >= threshold

def plot_route(route_points):
    route_latlon = [[lat, lon] for lon, lat in route_points]

    m = folium.Map(
        location=route_latlon[0],
        zoom_start=13,
        tiles=None
    )

    folium.TileLayer(
        tiles=f"https://api.mapbox.com/styles/v1/mapbox/streets-v12/tiles/{{z}}/{{x}}/{{y}}?access_token={mapbox_token}",
        attr="© Mapbox © OpenStreetMap",
        name="Mapbox Streets",
        tile_size=512,
        zoom_offset=-1
    ).add_to(m)

    folium.PolyLine(
        route_latlon,
        color="blue",
        weight=5,
        opacity=0.8
    ).add_to(m)

    # Highlight only nodes where the direction changes
    for i in range(1, len(route_points) - 1):
        lon1, lat1 = route_points[i - 1]
        lon2, lat2 = route_points[i]
        lon3, lat3 = route_points[i + 1]

        if (lat2 - lat1) * (lon3 - lon2) != (lat3 - lat2) * (lon2 - lon1):
            folium.CircleMarker(
                location=route_latlon[i],
                radius=6,
                color="red",
                fill=True,
                fill_color="red",
                fill_opacity=1,
                tooltip="Bend"
            ).add_to(m)

    folium.Marker(route_latlon[0], tooltip="Start").add_to(m)
    folium.Marker(route_latlon[-1], tooltip="Destination").add_to(m)

    m.fit_bounds(route_latlon)
    return m

#plot_route(get_route_points(get_location_by_address("tramstraat gent"), get_location_by_address("jozef plateau gebouw"))[2]).save("route_map.html")
print(get_route_points(get_location_by_address("overpoortstraat, gent"), get_location_by_address("jozef plateau gebouw, gent")))