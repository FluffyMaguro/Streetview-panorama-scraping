import asyncio
import json
import os
import traceback

import aiohttp

import streetview


async def download_tiles_async(tiles, directory, session):
    """ Downloads all the tiles in a Google Stree View panorama into a directory. """

    for i, (x, y, fname, url) in enumerate(tiles):
        # Try to download the image file
        url = url.replace("http://", "https://")
        while True:
            try:
                async with session.get(url) as response:
                    content = await response.read()
                    with open(directory + '/' + fname, 'wb') as out_file:
                        out_file.write(content)
                    break
            except:
                print(traceback.format_exc())


async def download_panorama(panoid,
                            session=None,
                            tile_diretory='tiles',
                            pano_directory='panoramas'):
    """ 
    Downloads a panorama from latitude and longitude
    Heavily IO bound (~98%), ~40s per panorama without using asyncio.
    """
    if not os.path.isdir(tile_diretory):
        os.makedirs(tile_diretory)
    if not os.path.isdir(pano_directory):
        os.makedirs(pano_directory)

    try:
        x = streetview.tiles_info(panoid['panoid'])
        await download_tiles_async(x, tile_diretory, session)
        streetview.stich_tiles(panoid['panoid'],
                               x,
                               tile_diretory,
                               pano_directory,
                               point=(panoid['lat'], panoid['lon']))
        streetview.delete_tiles(x, tile_diretory)

    except:
        print(f'Failed to create panorama\n{traceback.format_exc()}')


def panoid_created(panoid):
    """ Checks if the panorama was already created """
    file = f"{panoid['lat']}_{panoid['lon']}_{panoid['panoid']}.jpg"
    return os.path.isfile(os.path.join('panoramas', file))


async def download_loop(panoids, pmax):
    """ Main download loop """
    conn = aiohttp.TCPConnector(limit=100)
    async with aiohttp.ClientSession(connector=conn,
                                     auto_decompress=False) as session:
        try:
            await asyncio.gather(*[
                download_panorama(panoid, session=session)
                for panoid in panoids[:pmax] if not panoid_created(panoid)
            ])
        except:
            print(traceback.format_exc())


if __name__ == "__main__":

    # Load panoids info
    with open('panoids 89261.json', 'r') as f:
        panoids = json.load(f)

    print(f"Loaded {len(panoids)} panoids")

    # Download panorama in batches of 100
    loop = asyncio.get_event_loop()
    for i in range(1, 100):
        print(f'Running the next batch: {(i-1)*100+1} → {i*100}')
        loop.run_until_complete(download_loop(panoids, 100 * i))
