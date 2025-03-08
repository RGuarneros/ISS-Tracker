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


# xml_dict['ndm']['oem']['header']['CREATION_DATE'] # gets the creation date of data



# Parsing Arguments
parser = argparse.ArgumentParser()
parser.add_argument('-l', '--loglevel', type=str, required=False, default='WARNING',
                    help='set log level to DEBUG, INFO, WARNING, ERROR, or CRITICAL')
args = parser.parse_args() 

# Setting logging format 
format_str=f'[%(asctime)s {socket.gethostname()}] %(filename)s:%(funcName)s:%(lineno)s - %(levelname)s: %(message)s'
logging.basicConfig(level=args.loglevel, format=format_str)

app = Flask(__name__) 

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
    limit = request.args.get('limit',len(data)) # default is all dictionary 
    offset = request.args.get('offset',0) # default is no offset 
    try: 
        limit = int(limit) 
        offset = int(offset) 
    except ValueError: 
        return "Invalid limit/offset parameter; limit/offset must be integers \n" 
    result = data[offset:offset+limit] # AI used to slice data safely without for loop, its like MATLAB syntax 
    return result

@app.route('/epochs/<epoch>', methods=['GET']) # make a case where epoch is nonexistent
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
    specific_epoch = None
    for item in data:
        if item["EPOCH"] == epoch: 
            specific_epoch = item 
            break 
    if specific_epoch==None:
        return {"error": f"Epoch '{epoch}' not found"}, 404 # AI used to return 404 error
    return specific_epoch 

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
    return {'value':str(speed), 'units':' km/s'} 

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

    now_dict = now_epoch(data,"EPOCH")
    speed = get_epoch_speed(now_dict["EPOCH"])
    speed_val = speed["value"]
    now_dict["instant speed"] = speed_val 
    now_dict["units"] = "km/s"
    return [now_dict]

def now_epoch(list_of_dicts: List[dict],epoch_key: str) -> List[dict]: 
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
        if not list_of_dicts: logging.warning('Given list was empty')
        # current time
        now_time = time.mktime(time.gmtime())
        diff = m.inf
        closest_dict = {} 

        for item in list_of_dicts:
            # Calculating time
            # used ChatGPT to fix 000Z to %fZ in striptime func
            t = time.mktime(time.strptime(item[epoch_key], 
                                      '%Y-%jT%H:%M:%S.%fZ')) 
            if abs(now_time-t)<diff: 
                closest_dict = item
                diff = abs(now_time-t)

        return closest_dict
    except KeyError as e: 
        logging.error(f'Dictionary key not found: {e}\n') 
    except IndexError as e:
        logging.error(f'Index out of range: {e}\n')

def fetch_latest_iss_data():
    """Fetches the latest ISS ephemeris data and updates only if new data is available."""

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

def main():

    # if redis database empty then request data and write it to database
    rd=redis.Redis(host='127.0.0.1', port=6379, db=0)
    # check number of keys if empty it will return 0
    response_head = requests.head(url='https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml')
    header_time = response_head.headers['Last-Modified']
    # if header time is not the same then request new data
    if len(rd.keys())==0 or rd.get('Last-Modified') is not header_time: # order matters since an empty list cannot have a Last-modified time
        data = get_iss_data() 
        # write data to database inside if statement
        rd.set('Last-Modified',data[0]) # sets the last-modified value for reference
        # for loop to write each EPOCH to database for easier lookup         
        for item in data[1]: 
            rd.set(str(item['EPOCH']),json.dumps(item)) 
    # once the container is running, if it keeps running then check header every 24 hours
    # this will ensure you have most up to date data 



if __name__ == '__main__':
    main()
    app.run(debug=True, host='0.0.0.0')
