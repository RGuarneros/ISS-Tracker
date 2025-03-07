#!/usr/bin/env python3
from iss_tracker import now_epoch, speed_calc, range_of_data
import pytest 
import math
from typing import List
import requests

response1 = requests.get('http://localhost:5000/epochs')
epoch = response1.json()[30]['EPOCH']
response2 = requests.get('http://localhost:5000/epochs/'+epoch)
response3 = requests.get('http://localhost:5000/epochs/'+epoch+'/speed')
response4 = requests.get('http://localhost:5000/now')
response5 = requests.get('http://localhost:5000/epochs/a')
response6 = requests.get('http://localhost:5000/epochs/a/speed')

def test_epochs_route():
    assert response1.status_code == 200
    assert isinstance(response1.json(),list) == True

def test_specific_epoch_route(): 
    assert response2.status_code == 200
    assert isinstance(response2.json(),dict) == True
    assert response5.status_code == 404
    assert response2.json()["EPOCH"]==epoch

def test_specific_epoch_speed_route():
    assert response3.status_code == 200
    assert isinstance(response3.json(),dict) == True
    assert response6.status_code == 404
    assert len(response3.json()) == 2

def test_now_route():
    assert response4.status_code == 200
    assert isinstance(response4.json(),list) == True
    assert len(response4.json())==1
    assert len(response4.json()[0])==9 # 2 added entries for speed

# AI helped create these tests 
def test_now_epoch():
    data = [{'EPOCH': '2025-050T23:48:00.000Z', 'X': {'@units': 'km', '#text': '5870.8349256289102'}, 
             'Y': {'@units': 'km', '#text': '-2867.4525176072102'}, 'Z': {'@units': 'km', '#text':
             '1868.30956895554'}, 'X_DOT': {'@units': 'km/s', '#text': '3.62111898852819'}, 'Y_DOT':
             {'@units': 'km/s', '#text': '3.7289968226834902'}, 'Z_DOT': {'@units': 'km/s', '#text':
             '-5.6274091912002797'}}]
    assert type(now_epoch(data, 'EPOCH')) == dict # returns a dictionary
    assert now_epoch(data,'EPOCH') == data[0] # returns only item in data
    assert now_epoch(data,'EPOC') is None # EPOCH does not exist

def test_now_epoch_exceptions():
    data = [{'EPOCH': '2025-050T23:48:00.000Z', 'X': {'@units': 'km', '#text': '5870.8349256289102'}, 
             'Y': {'@units': 'km', '#text': '-2867.4525176072102'}, 'Z': {'@units': 'km', '#text':
             '1868.30956895554'}, 'X_DOT': {'@units': 'km/s', '#text': '3.62111898852819'}, 'Y_DOT':
             {'@units': 'km/s', '#text': '3.7289968226834902'}}]
    with pytest.raises(TypeError):
        now_epoch(data,[])
    with pytest.raises(ValueError):
        now_epoch([{'EPOCH': '2025-050T23:48:00.000'}], 'EPOCH')
    with pytest.raises(ValueError):
        now_epoch([{'EPOCH': '202-050T23:48:00.000'}], 'EPOCH')


def test_speed_calc():
    data = [{'EPOCH': '2025-050T23:48:00.000Z', 'X': {'@units': 'km', '#text': '5870.8349256289102'}, 
             'Y': {'@units': 'km', '#text': '-2867.4525176072102'}, 'Z': {'@units': 'km', '#text':
             '1868.30956895554'}, 'X_DOT': {'@units': 'km/s', '#text': '3.62111898852819'}, 'Y_DOT':
             {'@units': 'km/s', '#text': '3.7289968226834902'},'Z_DOT':{'@units': 'km/s', '#text': 
             '4.7289968226834902'}}]
    speed = math.sqrt(pow(3.62111898852819,2)+pow(3.7289968226834902,2)+pow(4.7289968226834902,2))
    assert speed_calc(data,['X_DOT','Y_DOT', 'Z_DOT', 'EPOCH'], ['@units', '#text']) == {"avg_speed": speed, "now_speed": speed} 
    data = [{'EPOCH': '2025-050T23:48:00.000Z', 'X': {'@units': 'km', '#text': '5870.8349256289102'}, 
             'Y': {'@units': 'km', '#text': '-2867.4525176072102'}, 'Z': {'@units': 'km', '#text':
             '1868.30956895554'}, 'X_DOT': {'@units': 'km/s', '#text': '3.62111898852819'}, 'Y_DOT':
             {'@units': 'km/s', '#text': '3.7289968226834902'},'Z_DOT':{'@units': 'km/s', '#text': 
             't'}}]
    assert speed_calc(data,['X_DO','Y_DOT', 'Z_DOT', 'EPOCH'],['@units', '#text']) == None
    assert speed_calc(data,['X_DOT','Y_DOT', 'Z_DOT', 'EPOCH'],[]) == None 
        
def test_speed_calc_exceptions():
    data = [{'EPOCH': '2025-050T23:48:00.000Z', 'X': {'@units': 'km', '#text': '5870.8349256289102'}, 
             'Y': {'@units': 'km', '#text': '-2867.4525176072102'}, 'Z': {'@units': 'km', '#text':
             '1868.30956895554'}, 'X_DOT': {'@units': 'km/s', '#text': 'r'}, 'Y_DOT':
             {'@units': 'km/s', '#text': '3.7289968226834902'},'Z_DOT':{'@units': 'km/s', '#text': 
             '4.7289968226834902'}}]
    with pytest.raises((ZeroDivisionError,ValueError)): 
        speed_calc(data,['X_DOT','Y_DOT', 'Z_DOT', 'EPOCH'],['@units', '#text'])
    with pytest.raises(ZeroDivisionError):
        speed_calc([],['X_DOT','Y_DOT', 'Z_DOT', 'EPOCH'], [])


def test_range_of_data(capfd):
    data = {'OBJECT_NAME': 'ISS', 'OBJECT_ID': '1998-067-A', 'CENTER_NAME': 'EARTH', 
             'REF_FRAME': 'EME2000', 'TIME_SYSTEM': 'UTC', 'START_TIME': '2025-048T12:00:00.000Z', 
             'STOP_TIME': '2025-063T12:00:00.000Z'}
    assert range_of_data(data,['START_TIME','STOP_TIME']) == None # doesnt return anything
    # AI used to capture terminal output
    range_of_data(data,['START_TIME','STOP_TIME'])
    captured = capfd.readouterr()
    assert "The provided data has a start time of: 2025-048T12:00:00.000Z," in captured.out 

def test_range_of_data_exceptions():
    data = [{'START_TIME': '2024-050T12:00:00.000Z', 'STOP_TIME': '2024-051T12:00:00.000Z'}]
    with pytest.raises(TypeError):
        range_of_data(data,['START_TIME','STOP_TIME'])
    with pytest.raises(TypeError):
        range_of_data(data, ['START_TIME'])  # Only one key provided
    with pytest.raises(TypeError):
        range_of_data(data, ['INVALID_START', 'INVALID_STOP'])
    data = None
    with pytest.raises(TypeError):
        range_of_data(data, ['START_TIME', 'STOP_TIME'])
    data = ['Not a dictionary']  # Invalid data format
    with pytest.raises(TypeError):
        range_of_data(data, ['START_TIME', 'STOP_TIME'])
    data = [{'START_TIME': '2024-050T12:00:00.000Z'}]  # Missing 'STOP_TIME'
    with pytest.raises(TypeError):
        range_of_data(data, ['START_TIME', 'STOP_TIME'])
    data = []
    with pytest.raises(ValueError):
        range_of_data(data, ['START_TIME', 'STOP_TIME'])

