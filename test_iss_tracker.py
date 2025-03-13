#!/usr/bin/env python3
from iss_tracker import get_iss_data, compute_location, now_epoch
import pytest 
import requests

def test_get_iss_data():
    data = get_iss_data()
    assert isinstance(data,tuple) == True 
    assert isinstance(data[0],str) == True 
    assert isinstance(data[1],list) == True 

def test_compute_location():
    data = {'EPOCH': '2025-020T00:00:00.000Z', 'X': {'@units': 'km', '#text': '5870.8349256289102'}, 
             'Y': {'@units': 'km', '#text': '-2867.4525176072102'}, 'Z': {'@units': 'km', '#text':
             '1868.30956895554'}, 'X_DOT': {'@units': 'km/s', '#text': '3.62111898852819'}, 'Y_DOT':
             {'@units': 'km/s', '#text': '3.7289968226834902'}, 'Z_DOT': {'@units': 'km/s', '#text':
             '-5.6274091912002797'}}
    result = compute_location(data) 
    assert isinstance(result,list) == True
    assert isinstance(result[0],float) == True
    assert isinstance(result[1],float) == True
    assert isinstance(result[2],float) == True
    assert isinstance(result[3],str) == True
    assert result[3] == "2025-01-20 00:00:00"

def test_now_epoch():
    data = ['2024-020T00:00:00.000Z', '2024-060T00:00:00.000Z', '2025-050T00:00:00.000Z'] 
    assert now_epoch('2025-020T00:00:00.000Z') == '2025-020T00:00:00.000Z' 
    assert now_epoch(['2025-020T00:00:00.000Z']) == '2025-020T00:00:00.000Z' 
    assert now_epoch(data) == '2025-050T00:00:00.000Z' 
    assert now_epoch([]) == []
    with pytest.raises(TypeError):
        now_epoch() 
    assert isinstance(now_epoch(data),str) == True 
    assert now_epoch(['a','vb']) == None 

def test_get_epochs_route(): # test for query parameters being infinity or something wrong 
    response = requests.get('http://localhost:5000/epochs') 
    assert response.status_code==200
    assert isinstance(response.json(),list) == True 
    assert isinstance(response.json()[34],dict) == True
    assert isinstance(response.json()[34]['EPOCH'],str) == True 
    response = requests.get('http://localhost:5000/epoch')
    assert response.status_code!=200
    entries_wanted = 2
    response = requests.get(f'http://localhost:5000/epochs?limit={entries_wanted}&offset=3') 
    assert response.status_code==200
    assert len(response.json())==2 # you only get the number of entries specified
    response = requests.get(f'http://localhost:5000/epochs?limit={entries_wanted}') 
    assert response.status_code==200
    response = requests.get('http://localhost:5000/epochs?limit=999999') 
    assert len(response.json())<999999

def test_get_epochs_route_exceptions():
    response = requests.get('http://localhost:5000/epochs?limit=9.4') 
    error_message = 'Invalid limit/offset parameter; limit/offset must be integers \n' 
    assert response.content.decode('utf-8')==error_message
    response = requests.get('http://localhost:5000/epochs?limit=9&offset=1.3') 
    assert response.content.decode('utf-8')==error_message
    response = requests.get('http://localhost:5000/epochs?limit=9.1&offset=1')
    assert response.content.decode('utf-8')==error_message
    response = requests.get('http://localhost:5000/epochs?limit=9.4&offset=1.1')
    assert response.content.decode('utf-8')==error_message

def test_specific_epoch_route(): 
    response = requests.get('http://localhost:5000/epochs') 
    epoch = response.json()[34]['EPOCH'] 
    response = requests.get(f'http://localhost:5000/epochs/{epoch}') 
    assert response.status_code==200 
    assert isinstance(response.json(),dict) == True 
    assert response.json()['EPOCH'] == epoch 
    assert isinstance(response.json()['X_DOT'],dict) == True 
    assert isinstance(response.json()['X_DOT']['#text'],str) == True 
    # Wrong epoch 
    response = requests.get(f'http://localhost:5000/epochs/a') 
    assert isinstance(response.json(),dict)==True
    assert response.status_code==404 

def test_specific_epoch_speed_route(): 
    response = requests.get('http://localhost:5000/epochs') 
    epoch = response.json()[34]['EPOCH'] 
    response = requests.get(f'http://localhost:5000/epochs/{epoch}/speed') 
    assert response.status_code==200 
    assert isinstance(response.json(),dict) == True 
    assert isinstance(response.json()['speed'],str) == True 
    assert isinstance(response.json()['units'],str) == True 
    # Wrong Epoch 
    response = requests.get(f'http://localhost:5000/epochs/a/speed') 
    assert isinstance(response.json(),dict)==True # get the same output as getting epoch error
    assert response.status_code==404 

def test_specific_epoch_location_route(): 
    response = requests.get('http://localhost:5000/epochs') 
    epoch = response.json()[34]['EPOCH'] 
    response = requests.get(f'http://localhost:5000/epochs/{epoch}/location') 
    assert response.status_code==200 
    assert isinstance(response.json(),dict) == True 
    assert len(response.json()) == 5 
    assert type(response.json()['latitude'])==float
    assert type(response.json()['longitude'])==float 
    assert type(response.json()['epoch_timestamp'])==str 
    assert type(response.json()['altitude'])==float 
    assert type(response.json()['geoposition'])==str 
    # Wrong epoch
    response = requests.get(f'http://localhost:5000/epochs/a/location') 
    assert isinstance(response.json(),dict)==True # get the same output as getting epoch error
    assert response.status_code==404 

def test_now_route(): 
    response = requests.get('http://localhost:5000/now') 
    assert response.status_code==200 
    assert isinstance(response.json(),dict) == True 
    assert len(response.json()) == 7 
    assert type(response.json()['latitude'])==float
    assert type(response.json()['longitude'])==float 
    assert type(response.json()['epoch_timestamp'])==str 
    assert type(response.json()['altitude'])==float 
    assert type(response.json()['geoposition'])==str 
    assert type(response.json()['speed'])==str 
    assert type(response.json()['now_timestamp'])==str 
    