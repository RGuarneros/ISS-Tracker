#!/usr/bin/env python3
import requests
import xmltodict
import argparse
import logging
import socket
from typing import List
import math as m
import time
from flask import Flask, request
import json
import redis
import threading
from astropy import coordinates 
from astropy import units 
from geopy.geocoders import Nominatim 

# Parsing Arguments
parser = argparse.ArgumentParser()
parser.add_argument('-l', '--loglevel', type=str, required=False, default='WARNING',
                    help='set log level to DEBUG, INFO, WARNING, ERROR, or CRITICAL')
args = parser.parse_args() 

# Setting logging format 
format_str=f'[%(asctime)s {socket.gethostname()}] %(filename)s:%(funcName)s:%(lineno)s - %(levelname)s: %(message)s'
logging.basicConfig(level=args.loglevel, format=format_str)

rd=redis.Redis(host='127.0.0.1', port=6379, db=0)

app = Flask(__name__) 

def fetch_latest_iss_data():
    """Fetches the latest ISS ephemeris data and updates only if new data is available."""
    # if redis database empty then request data and write it to database
    # check number of keys if empty it will return 0 
    response_head = requests.head(url='https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml')
    header_time = response_head.headers['Last-Modified']
    # if header time is not the same then request new data
    if len(rd.keys())==0 or rd.get('Last-Modified').decode('utf-8') != header_time: # order matters since an empty list cannot have a Last-modified time
        logging.debug('Data was not the same, initializing update.')
        data = get_iss_data() 
        # write data to database inside if statement
        rd.set('Last-Modified',data[0]) # sets the last-modified value for reference
        # for loop to write each EPOCH to database for easier lookup         
        for item in data[1]: 
            rd.set(str(item['EPOCH']),json.dumps(item)) # redis saves it in random order 
        logging.info('Data has been updated.')
    else:
        logging.debug('Data was the same.')
    # once the container is running, if it keeps running then check header every 24 hours
    # this will ensure you have most up to date data 

def get_iss_data():
    # Getting data from NASA's Website using the requests library 
    try: 
        response = requests.get(url='https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml') 
        response_head = requests.head(url='https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml')
        if response.status_code!=200: # return status code --> 200 is success 
            logging.error(f'Status Error: {response.status_code}') 
            raise Exception(f'Status Error: {response.status_code}') 
        xml_dict = xmltodict.parse(response.content) # parses data from xml to dictionary
        logging.debug(f'Data has been successfully written to data as a {type(xml_dict)}\n')
        data = xml_dict['ndm']['oem']['body']['segment']['data']['stateVector'] 
        # each index is its own dictionary with EPOCH, X, Y, Z, X_DOT, Y_DOT, Z_DOT --> each one has @units and #text 
        return response_head.headers['Last-Modified'], data # --> returns as tuple 
    except FileNotFoundError: 
        logging.error(f'The specified key does not exist\n') 
        raise Exception(f'The specified key does not exist\n')

# AI used to create background updater 
def background_updater():
    while True: # infinite loop to keep updating 
        fetch_latest_iss_data()
        logging.info('Sleeping for 24 hours before next check...')
        time.sleep(86400) 

# Start background updater in a separate thread --> AI used 
threading.Thread(target=background_updater, daemon=True).start()


@app.route('/epochs', methods=['GET'])
def get_epochs(): # gets data from url 
    """
    This route uses the GET method to retrieve the entire data set. 
    It also allows query parameters to return a modified list of Epochs 
    according to the limit and offset values given. 

    Args: 
        NONE 

    Returns: 
        result (list): Returns the list of dictionaries according to 
                       some limit and offset values.
    """ 
    limit = request.args.get('limit',len(rd.keys())-1) # default is whole database without header
    offset = request.args.get('offset',0) # default is no offset 
    try: 
        limit = int(limit) 
        offset = int(offset) 
    except ValueError: 
        return "Invalid limit/offset parameter; limit/offset must be integers \n" 
    keys = [key.decode('utf-8') for key in rd.keys() if key.decode('utf-8') != "Last-Modified"] # AI used to check for last modified entry
    keys.sort() # AI mentioned sort function
    keys_to_get = keys[offset:offset+limit]
    data = [] 
    for epoch in keys_to_get:
        data.append(json.loads(rd.get(epoch).decode('utf-8')))
    return data

@app.route('/epochs/<epoch>', methods=['GET']) 
def get_epoch(epoch):
    """
    This route uses the GET method to retrieve a certain epoch and its 
    state vectors from the data set. 

    Args: 
        epoch (string): A string specifying the value of the epoch you 
                        want to extract. 

    Returns: 
        result (dict): Returns the dictionary with the epoch value you specified. 
    """
    try: 
        specific_epoch = json.loads(rd.get(epoch).decode('utf-8')) # returns dictionary 
        return specific_epoch
    except AttributeError as e:
        return {"error": f"Epoch '{epoch}' not found"}, 404 # AI used to return 404 error 

@app.route('/epochs/<epoch>/speed', methods=['GET']) 
def get_epoch_speed(epoch):
    """
    This route uses the GET method to retrieve a certain epoch and calculate 
    the cartesian speed of that epoch using its state vectors. 

    Args: 
        epoch (string): A string specifying the value of the epoch you 
                        want to calculate the speed of. 

    Returns: 
        result (str): Returns a string representing the speed of the epoch 
                      you specified.  
    """
    specific_epoch = get_epoch(epoch)
    if isinstance(specific_epoch, tuple) and specific_epoch[1]==404: # AI used to implement more checks
        return {"error": f"No data available for epoch '{epoch}'."}, 404
    # Extracting values 
    x_dot = float(specific_epoch["X_DOT"]["#text"]) 
    y_dot = float(specific_epoch["Y_DOT"]["#text"]) 
    z_dot = float(specific_epoch["Z_DOT"]["#text"]) 
    # Calculating speed 
    speed = m.sqrt(m.pow(x_dot,2)+m.pow(y_dot,2)+m.pow(z_dot,2)) 
    return {'speed':str(speed), 'units':' km/s'} 

@app.route('/epochs/<epoch>/location', methods=['GET']) 
def get_epoch_location(epoch):  
    epoch_data = get_epoch(epoch)
    if type(epoch_data)!=dict:  
        return epoch_data
    vals = compute_location(epoch_data)
    geocoder = Nominatim(user_agent='iss_tracker')
    geoloc = geocoder.reverse((vals[0], vals[1]), exactly_one=True, language='en', zoom=18)
    # AI was used to clean up output 
    geoposition = geoloc.address.encode('ascii', 'ignore').decode() if geoloc else 'Above a sea, no address available.'
    if not geoloc: 
        geoposition = 'Above a sea, no address available.' 
    return {'latitude':vals[0], 'longitude':vals[1], 'altitude':vals[2], 
            'geoposition':geoposition.strip(" -,"), 'epoch_timestamp':vals[3]} 

def compute_location(epoch_dict): 
    if type(epoch_dict)==dict:
        x = float(epoch_dict['X']['#text'])
        y = float(epoch_dict['Y']['#text'])
        z = float(epoch_dict['Z']['#text'])
    else: 
        return {"error": f"Epoch '{epoch_dict}' not found"}, 404
    # assumes epoch is in format '2024-067T08:28:00.000Z'
    this_epoch=time.strftime('%Y-%m-%d %H:%M:%S', time.strptime(epoch_dict['EPOCH'][:-5], '%Y-%jT%H:%M:%S'))
    cartrep = coordinates.CartesianRepresentation([x, y, z], unit=units.km)
    gcrs = coordinates.GCRS(cartrep, obstime=this_epoch) 
    itrs = gcrs.transform_to(coordinates.ITRS(obstime=this_epoch))
    loc = coordinates.EarthLocation(*itrs.cartesian.xyz) 
    return [loc.lat.value, loc.lon.value, loc.height.value, this_epoch]

@app.route('/now', methods=['GET'])
def now_speed(): 
    """
    This route uses the GET method to retrieve the epoch nearest to 
    the current time and calculate the cartesian speed of that epoch.  

    Args: 
        NONE

    Returns: 
        result (dict): Returns a dictionary of the closest epoch to the 
                       current time, its state vectors and its calculated
                       speed. 
    """

    keys = [key.decode('utf-8') for key in rd.keys() if key.decode('utf-8') != "Last-Modified"] 
    now_epoch_label = now_epoch(keys) 
    speed = get_epoch_speed(now_epoch_label) 
    loc = get_epoch_location(now_epoch_label) 
    loc["speed"] = speed["speed"] + speed["units"] 
    loc["now_timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S",time.gmtime())
    return loc 

def now_epoch(list_of_keys: List[str]) -> str: 
    """
    This function gets a list of dictionaries with a time stamp, state vectors
    and velocities. It identifies the closest epoch to "now".

    Args: 
        list_of_dicts (list): A list of dictionaries, each dictionary 
                              should have the specified keys. 
        epoch_key (string): A string representing the key for the epoch label
                            (i.e. 'EPOCH') 

    Returns:
        closest_dict (dictionary): Returns the dictionary closest to "now". 
    """  

    try: 
        if not list_of_keys: logging.warning('Given list was empty')
        # current time
        now_time = time.mktime(time.gmtime())
        diff = m.inf

        for epoch in list_of_keys:
            # Calculating time
            # used ChatGPT to fix 000Z to %fZ in striptime func
            t = time.mktime(time.strptime(epoch, '%Y-%jT%H:%M:%S.%fZ')) 
            if abs(now_time-t)<diff: 
                closest_epoch = epoch
                diff = abs(now_time-t)

        return closest_epoch
    except KeyError as e: 
        logging.error(f'Dictionary key not found: {e}\n') 
    except IndexError as e:
        logging.error(f'Index out of range: {e}\n')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
