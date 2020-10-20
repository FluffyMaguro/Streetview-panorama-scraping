import json
import math
import asyncio
import itertools
import traceback
import webbrowser
from pprint import pprint

import aiohttp
import folium

import streetview


async def get_panoid(lat, lon, session):
    """ Get data about panoids asynchronously """
    try:
        url = f"https://maps.googleapis.com/maps/api/js/GeoPhotoService.SingleImageSearch?pb=!1m5!1sapiv3!5sUS!11m2!1m1!1b0!2m4!1m2!3d{lat}!4d{lon}!2d50!3m10!2m2!1sen!2sGB!9m1!1e2!11m4!1m3!1e2!2b1!3e2!4m10!1e1!1e2!1e3!1e4!1e8!1e6!5m1!1e2!6m1!1e2&callback=_xdc_._v2mub5"
        async with session.get(url) as resp:
            assert resp.status == 200
            text = await resp.text()
            panoids = streetview.panoids_from_response(text)
            all_panoids.extend(panoids)
    except:
        print('timeout')
        await asyncio.sleep(10)
        await get_panoid(lat, lon, session)


async def request_loop():
    conn = aiohttp.TCPConnector(limit=100)
    async with aiohttp.ClientSession(connector=conn) as session:
        try:
            await asyncio.gather(*[get_panoid(*point, session) for point in test_points])
        except:
            print(traceback.format_exc())


def distance(p1, p2):
    """ Haversine formula: returns distance for latitude and longitude coordinates"""
    R = 6373
    lat1 = math.radians(p1[0])
    lat2 = math.radians(p2[0])
    lon1 = math.radians(p1[1])
    lon2 = math.radians(p2[1])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R*c


if __name__ == "__main__":
    """ Downloads and saves info about panoids in region"""

    # Init variables
    file = 'Result.html'
    zoom_start = 12

    ### CONFIGURATION
    center = (50.7734, 14.2080) # Center of area
    radius = 3 # Radius in kilometres
    resolution = 500 # How many dummy points are searched, lower makes it faster, but some panoramas will be missed


    top_left = (center[0]-radius/70, center[1]+radius/70)
    bottom_right = (center[0]+radius/70, center[1]-radius/70)

    lat_diff = top_left[0] - bottom_right[0]
    lon_diff = top_left[1] - bottom_right[1]

    # Create map
    M = folium.Map(location=center, tiles='OpenStreetMap', zoom_start=zoom_start)

    # Show lat/lon popups
    M.add_child(folium.LatLngPopup())

    # Mark Area
    folium.Circle(location=center, radius=radius*1000, color='#FF000099', fill='True').add_to(M)

    # Get testing points
    test_points = list(itertools.product(range(resolution+1), range(resolution+1)))
    test_points = [(bottom_right[0] + x*lat_diff/resolution, bottom_right[1] + y*lon_diff/resolution) for (x,y) in test_points]
    test_points = [p for p in test_points if distance(p, center) <= radius]
    
    ### Show test points
    # for point in test_points:
    #     folium.Circle(location=point, radius=1, color='red').add_to(M)

    # Run asynchronous loop to get data about panos
    all_panoids = list()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(request_loop())

    # Filter out duplicates
    print(f'Pre-filtering: {len(all_panoids)} panoramas')
    
    already_in = set()
    new_all_panoids = list()
    for pan in all_panoids:
        if not pan['panoid'] in already_in:
            already_in.add(pan['panoid'])
            new_all_panoids.append(pan)

    print(f'Post-filtering: {len(new_all_panoids)} panoramas')

    # Add points streetview locations
    for pan in new_all_panoids:
        folium.CircleMarker([pan['lat'], pan['lon']], popup=pan['panoid'], radius=1, color='blue', fill=True).add_to(M)

    # Save data
    with open(f'panoids_{len(new_all_panoids)}.json','w') as f:
        json.dump(new_all_panoids, f, indent=2)

    ## Save map and open it
    M.save(file)
    webbrowser.open(file)
