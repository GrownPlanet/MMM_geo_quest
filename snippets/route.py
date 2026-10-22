import requests
import geocoder
import folium

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


    folium.Marker(route_latlon[0], tooltip="Start").add_to(m)
    folium.Marker(route_latlon[-1], tooltip="Destination").add_to(m)

    m.fit_bounds(route_latlon)

    return m

#plot_route(get_route_points(get_current_location(), get_location_by_address("Groeneweg 43, 987 Olsene"))[2]).save("route_map.html")