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

app = Flask(__name__)

parser = argparse.ArgumentParser()
parser.add_argument('-l', '--loglevel', type=str, required=False, default='WARNING',
                    help='set log level to DEBUG, INFO, WARNING, ERROR, or CRITICAL')
args = parser.parse_args()

format_str=f'[%(asctime)s {socket.gethostname()}] %(filename)s:%(funcName)s:%(lineno)s - %(levelname)s: %(message)s'
logging.basicConfig(level=args.loglevel, format=format_str)

try: 
    response = requests.get(url='https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml') 
    if response.status_code!=200: # return status code --> 200 is success 
        logging.error(f'Status Error: {response.status_code}') 
        raise Exception(f'Status Error: {response.status_code}') 
    xml_dict = xmltodict.parse(response.content) # parses data from xml to dictionary
    logging.debug(f'Data has been successfully written to data as a {type(xml_dict)}\n')
    data = xml_dict['ndm']['oem']['body']['segment']['data']['stateVector'] 
    # each index is its own dictionary with EPOCH, X, Y, Z, X_DOT, Y_DOT, Z_DOT --> each one has @units and #text 
except FileNotFoundError: 
    logging.error(f'The specified key does not exist\n') 

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

def range_of_data(list_of_dicts: List[dict], keys: List[str]):
    """
    This function gets a list of dictionaries with metadata segment. 
    It prints a statement about the range of data using timestamps 
    from the first and last epochs.

    Args: 
        list_of_dicts (list): A list of dictionaries, each dictionary 
                              should have the specified keys. 
        keys (list): A list of strings representing the keys for the start 
                     and end epoch. (i.e. ['START_TIME','STOP_TIME']) 

    Returns:
        NONE
    """  

    try: 
        if len(list_of_dicts)==0:
            logging.error('Given list was empty')
            raise ValueError
        print(f'The provided data has a start time of: {list_of_dicts[keys[0]]},') 
        print(f'and an end time of: {list_of_dicts[keys[1]]}\n')
    except KeyError as e: 
        logging.error(f'Dictionary key not found: {e}\n') 
    except IndexError as e:
        logging.error(f'Index out of range: {e}\n')


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


def speed_calc(list_of_dicts: List[dict], keys_for_dict: List[str], 
               keys_for_data: List[str]) -> dict: 
    """
    This function gets a list of dictionaries with velocity components in 
    Cartesian coordinates. It calculates the average of the speed over the 
    whole data set, as well as the instantaneous speed closest to "now". 

    Args: 
        list_of_dicts (list): A list of dictionaries, each dictionary 
                              should have the specified keys. 
        keys_for_dict (list): A list of strings for the keys that 
                                  pertain to velocities in the x, y, z 
                                  direction and epoch. (i.e.['X_DOT', 
                                  'Y_DOT', 'Z_DOT', 'EPOCH']) 
        keys_for_data (list): A list of strings for the keys petaining 
                              to the units and value of velocity. 
                              (i.e. ['#units','#text'])

    Returns:
        dict: Returns the average of speeds and the now speed in a 
                      dictionary. (i.e. {"avg_speed": "value1", 
                      "now_speed": "value2"})
    """  
    try:
        if not list_of_dicts: logging.warning(print('Given list was empty'))
        # initializing values    
        now_time = time.mktime(time.gmtime())
        diff = m.inf # initialized as infinity
        now_speed = None
        list_of_speeds = []

        for item in list_of_dicts:
            # Extracting values
            x_dot = float(item[keys_for_dict[0]][keys_for_data[1]])
            y_dot = float(item[keys_for_dict[1]][keys_for_data[1]])
            z_dot = float(item[keys_for_dict[2]][keys_for_data[1]])
            # Calculating values
            speed = m.sqrt(m.pow(x_dot,2)+m.pow(y_dot,2)+m.pow(z_dot,2))
            logging.debug(f'Speed calculated successfully\n')
            list_of_speeds.append(speed) # saving speeds to list
            # Calculating time
            # used ChatGPT to fix 000Z to %fZ in striptime func
            t = time.mktime(time.strptime(item[keys_for_dict[3]], 
                                  '%Y-%jT%H:%M:%S.%fZ')) 
            if abs(now_time-t)<diff: 
                now_speed = speed
                diff = abs(now_time-t)
        avg = sum(list_of_speeds)/len(list_of_dicts)

        return {"avg_speed": avg, "now_speed": now_speed}
    except KeyError as e: 
        logging.error(f'Dictionary key not found: {e}\n') 
    except IndexError as e:
        logging.error(f'Index out of range: {e}\n')


def main():
    # Prints statement about range of data using timestamps from first to last epochs
    range_of_data(xml_dict['ndm']['oem']['body']['segment']['metadata'],['START_TIME','STOP_TIME'])

    # Prints full epoch closest to now
    closest = now_epoch(data,'EPOCH')
    print(f'Full epoch closest to now is:')
    print(f'{closest}\n')

    # calculates and prints average speed and instantaneous speed closest to now
    speed = speed_calc(data,['X_DOT','Y_DOT','Z_DOT','EPOCH'],['#units','#text'])
    units = data[0]['X_DOT']['@units']
    print(f'Average speed and instantaenous speed closest to now are:')
    print(f'{speed} {units}\n')
    

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
    main()
