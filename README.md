# ISS Tracker: Containerized Flask App - Real Time ISS Geolocation Calculator & ISS Past and Future Position and Velocity Retrieval 

## Table of Contents
1. [Description](README.md#description)
2. [Software Diagram](README.md#software-diagram)
2. [ISS Trajectory Data Set](README.md#iss-trajectory-data-set)
2. [Getting Started](README.md#getting-started)
3. [Building the Container](README.md#building-the-container)
4. [Running Docker Container](README.md#running-docker-container)
5. [Accessing Microservice](README.md#accessing-microservice) 
6. [Running Test Script](README.md#running-test-script)
7. [Clean Up](README.md#clean-up)
9. [Resources](README.md#resources)
10. [AI Usage](README.md#ai-usage)

## Description 

This code features five routes in a containerized flask app that is communicating with a [redis](https://redis.io) databse. The ```iss_tracker.py``` establishes connection with a redis database and checks if database is empty. If empty or if the data is out of date, it injests the [ISS Trajectory Data](https://spotthestation.nasa.gov/trajectory_data.cfm) using the requests library and writes it to the redis database as ```key:value``` pairs. You are able to return the whole data set or a modified list of epochs by using query parameters as well as return a specific epoch and its geolocation. There exists a final route which can return the epoch closest to the current time, its instantaneous speed, latitude, longitude, altitude, and geoposition. 

The iss_tracker script also contains four functions of the names: 
* now_epoch - Identifies which epoch is closest to the current time. This will change based on when you run the script. 
* compute_location - Calculates the latitude, longitude, and altitude from state vectors in cartesian coordinates using the geopy library. 
* get_iss_data - Gets the ISS state vectors at different epochs from Spot The Station website using the requests library. 
* fetch_latest_iss_data - Fetches the latest ISS ephemeris data and updates redis database only if new data is available.  

The main script also features a background process that calls the fetch_latest_iss_data function every 6 hours to make sure you have the latest ISS data. This becomes useful when you have the container up and running for a long time (i.e. 36 hours), you do not have to restart your iss_tracker.py script, it will automatically look for the most up to date data. 


Here are the 5 routes metioned above and their syntax: 

|  Route                        |  Method  | Functionality                                                                      |
| ----------------------------- | -------- | ---------------------------------------------------------------------------------- |
| /epochs                       | GET      | Return entire data set                                                             |
| /epochs?limit=int&offset=int  | GET      | Return modified list of Epochs given query parameters                              | 
| /epochs/{epoch}               | GET      | Return state vectors for a specific Epoch from the data set                        | 
| /epochs/{epoch}/speed         | GET      | Return instantaneous speed for a specific Epoch in the data set                    | 
| /epochs/{epoch}/location      | GET      | Return latitude, longitude, altitude, and geoposition for a specific Epoch in the data set | 
| /now                          | GET      | Return instantaneous speed, latitude, longitude, altitude, and geoposition for the Epoch that is nearest in time | 

This project illustrates how to ingest data from a Web API using the ```requests``` library and saving this data to a redis database. It also helps facilitate the analysis of such data by using the four functions and five routes mentioned above. 

This code is necessary when you want to constantly have the updated data to your disposal for analysis but would like to securely save it to a database. It facilitates running some calculations on the most up to date data. It also allows the user to get the current geolocation of the ISS in real time. If you would like a visualization tool please go to https://www.n2yo.com/?s=90027. 

## Software Diagram
![Software Diagram](diagram.png "Software Diagram Flowchart") 

This diagram shows the typical flow of data focused around the files of homework05. We can clearly see that the docker container pulls data from the NASA's ISS Trajectory Database using the requests library. The iss_tracker.py inside the docker container converts the xml response from the database into a json like list of dictionaries that we can analyze, illustrated by the data block. This is done outside any routes for a faster runtime. The get_data() function uses this variable called "data" to return that same data depending the query parameters. The function get_epoch() also uses this retrieved data to look for a specific epoch and returns the epoch and its state vectors as a dictionary. The get_epoch_speed() function uses the retrieved state vectors of a specified epoch to calculate the cartesian speed of that epoch. Finally, the now_speed() uses the previously defined now_epoch() and the get_epoch_speed() function to calculate the instantaneous speed of the nearest epoch to the current time. 

The user is able to interact with the containerised flask application using the ```curl``` command. Running the illustrated routes using the ```curl localhost:5000``` and proper query parameters, it allows the user to call each each containerized function and analyze the ISS Trajectory Data. 

## ISS Trajectory Data Set 
The [ISS Trajectory Data](https://spotthestation.nasa.gov/trajectory_data.cfm) provides the most current posted ephemeris available in .txt and .xml file format. Each file contains header lines with the ISS mass in kg, drag area in m2, and drag coefficient used in generating the ephemeris. The header also contains lines with details for the first and last ascending nodes within the ephemeris span. Following this is a listing of upcoming ISS translation maneuvers, called “reboosts,” and visiting vehicle launches, arrivals, and departures. 

After the header, ISS state vectors in the Mean of J2000 (J2K) reference frame are listed at four-minute intervals spanning a total length of 15 days. During reboosts (translation maneuvers), the state vectors are reported in two-second intervals. Each state vector lists the time in UTC; position X, Y, and Z in km; and velocity X, Y, and Z in km/s.

For more information please follow this link: https://spotthestation.nasa.gov/trajectory_data.cfm. 

Disclaimer: The following description represents the same description from NASA's website. 

## Getting Started
### Dependencies

[Docker](https://www.google.com/search?client=safari&rls=en&q=installing+docker+in+ubuntu&ie=UTF-8&oe=UTF-8) is used so please make sure to install it before running any docker commands. 

Please follow the instructions to install ```Docker``` from the link provided above. 

### Clone this repo 

```bash
git clone git@github.com:RGuarneros/ISS-Tracker.git

cd ISS-Tracker 
```

Make sure to ```cd``` into the ISS-Tracker folder in order to build the correct image. 

### Create ./data directory
IMPORTANT: Make sure to make a directory called ```data```. This will serve as the dump folder for the redis backup. This assures that the redis database is truly persistent. 

```bash
mkdir data 
```

## Building the Container 

To build the image from the provided Dockerfile run: 
``` bash
docker build -t username/flask-redis-iss_tracker:1.0 . 

# Example
docker build -t rguarneros065/flask-redis-iss_tracker:1.0 . 
```
Make sure to replace 'username' with your Docker Hub username. 

To ensure you see a copy of your image that was built, run 
``` bash 
docker images 

# Example Output
REPOSITORY                              TAG       IMAGE ID       CREATED        SIZE
rguarneros065/flask-redis-iss_tracker   1.0       79a42c298d51   11 hours ago   1.21GB
...

``` 

You should see your username in the repository name. 

## Running Docker Container
Before using the  ```docker compose up``` verb, we have to make some small changes to our docker-compose.yml file. First, let's make sure that we don't have any container using port 5000 by running: 
```bash
docker ps -a

# NO CONTAINERS LISTENING TO PORT 5000 EXAMPLE 
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
```
Under the PORTS section, no containers should be listening in to port 5000. If there are containers listening to port 5000 make sure to stop and remove them using the following commands: 
```bash 
docker stop <CONTAINER_ID> 

docker rm <CONTAINER_ID> 
``` 

Now we can proceed to configuring our docker-compose.yml file. 
As you may have noticed, you have a [docker-compose.yml](docker-compose.yml) file. You will have to modify this to be able to run docker compose. 

Using your favorite text editor (i.e vim, emacs, nano, etc), open this file and change 'username' to your docker username. 
```bash
# Example
vim docker-compose.yml 

# Output
--- 
version: "3"

services:
    redis-db:
        image: redis:7
        ports:
            - 6379:6379
        volumes:
            - ./data:/data
        user: "1000:1000"
        command: ["--save", "1", "1"]
    flask-app:
        build:
            context: ./
            dockerfile: ./Dockerfile
        depends_on:
            - redis-db
        image: username/flask-redis-iss_tracker:1.0
        ports:
            - 5000:5000
```
Please make sure to change 'username' to your actual docker username. 

Now you are ready to run docker compose. 
```bash 
docker compose up -d

# Output
WARN[0000] /home/ubuntu/ISS-Tracker/docker-compose.yml: `version` is obsolete 
[+] Running 3/3
 ✔ Network iss-tracker_default        Created                                                                                                            0.1s 
 ✔ Container iss-tracker-redis-db-1   Started                                                                                                            0.5s 
 ✔ Container iss-tracker-flask-app-1  Started                                                                                                            0.7s 
```
The -d flag allows you to start the service in the background. 

Make sure the container is up and running:
```bash 
docker ps -a 

# Output
CONTAINER ID   IMAGE                                       COMMAND                  CREATED          STATUS          PORTS                                       NAMES
262163a8e775   rguarneros065/flask-redis-iss_tracker:1.0   "python iss_tracker.…"   38 seconds ago   Up 37 seconds   0.0.0.0:5000->5000/tcp, :::5000->5000/tcp   iss-tracker-flask-app-1
23f2af42b4fe   redis:7                                     "docker-entrypoint.s…"   38 seconds ago   Up 37 seconds   0.0.0.0:6379->6379/tcp, :::6379->6379/tcp   iss-tracker-redis-db-1
... 
``` 

You should see 2 containers are up and running. This is due to the iss_tracker need to establish a connection with the redis database while hosting the flask app. 

Your container list should have a container with the name you gave it, an Up status, and the port mapping you specified in the docker-compose.yml file.  

## Accessing Microservice
Now you are ready to run your Flask microservice! 

### Running '/epochs' route 
To return the entire data set you can run: 
``` bash
curl "localhost:5000/epochs"

# Output
[
  {
    "EPOCH": "2025-052T12:00:00.000Z",
    "X": {
      "#text": "-1627.01220187592",
      "@units": "km"
    },
    "X_DOT": {
      "#text": "-7.1308965092829402",
      "@units": "km/s"
    },
    "Y": {
      "#text": "4599.2962205130698",
      "@units": "km"
    },
    "Y_DOT": {
      "#text": "0.32375775761575998",
      "@units": "km/s"
    },
    "Z": {
      "#text": "-4733.4531236806697",
      "@units": "km"
    },
    "Z_DOT": {
      "#text": "2.7667916377209498",
      "@units": "km/s"
    }
  }, 
  ...
]

```
The following command returned a list of dictionaries containing the EPOCH, X, Y, Z, X_DOT, Y_DOT, and Z_DOT values for each. It is getting all the epoch dictionaries from the redis database and displaying them to the user in the terminal. 

### Running '/epochs?limit=int&offset=int' route 
You can also return a certain number of epochs with a certain offset. This is done using query parameters as follows: 
```bash 
curl "localhost:5000/epochs?limit=int&offset=int"

# Example
curl "localhost:5000/epochs?limit=1&offset=4"

# Output
[
  {
    "EPOCH": "2025-052T12:16:00.000Z",
    "X": {
      "#text": "-6351.9707892400202",
      "@units": "km"
    },
    "X_DOT": {
      "#text": "-1.7301970697409399",
      "@units": "km/s"
    },
    "Y": {
      "#text": "2416.67730860454",
      "@units": "km"
    },
    "Y_DOT": {
      "#text": "-4.4220746956527099",
      "@units": "km/s"
    },
    "Z": {
      "#text": "-53.224668333840903",
      "@units": "km"
    },
    "Z_DOT": {
      "#text": "6.0135920755168097",
      "@units": "km/s"
    }
  }
]
```
The following command returned the specified number of epoch(s), in this case 1, starting at the fifth epoch as specified by an offset value of 4. 

If you leave offset empty, it will default to zero offset. Note that if you run: 
```bash 
curl "localhost:5000/epochs?limit=99999&offset=0"
```
OR
```bash
curl "localhost:5000/epochs?limit=99999" 
```
The entire data set will be returned. 

### Running '/epochs/<epoch>' route 
You are also able to return a specific epoch using the following route: 
``` bash 
curl "localhost:5000/epochs/<epoch>"

# Example
curl "localhost:5000/epochs/2025-052T12:16:00.000Z"

# Output
{
  "EPOCH": "2025-052T12:16:00.000Z",
  "X": {
    "#text": "-6351.9707892400202",
    "@units": "km"
  },
  "X_DOT": {
    "#text": "-1.7301970697409399",
    "@units": "km/s"
  },
  "Y": {
    "#text": "2416.67730860454",
    "@units": "km"
  },
  "Y_DOT": {
    "#text": "-4.4220746956527099",
    "@units": "km/s"
  },
  "Z": {
    "#text": "-53.224668333840903",
    "@units": "km"
  },
  "Z_DOT": {
    "#text": "6.0135920755168097",
    "@units": "km/s"
  }
}
```
This command only returned the specified dictionary with that certain epoch value and its state vectors. 

### Running '/epochs/<epoch>/speed' route 
If you want to calculate the speed of a specific epoch, you are able to do so with the following command:
```bash
curl "localhost:5000/epochs/<epoch>/speed" 

# Example
curl "localhost:5000/epochs/2025-084T12:00:00.000Z/speed" 

# Output
{
  "speed": "7.665487953704597",
  "units": " km/s"
}

```
As seen above, this route calculates the speed of the specified epoch using the square root of the sum of squares of its cartesian components. It returned a dictionary with key:pair values for speed and units. 

### Running '/now' route 
Another functionality of the application is returning latitude, longitude, altitude, geoposition, and instantaneous speed for the Epoch that is nearest in time. 
This is available with the following route:
```bash
curl "localhost:5000/now"

# Example Output
{
  "altitude": 421.2265225359128,
  "epoch_timestamp": "2025-03-13 19:00:00",
  "geoposition": "Above a sea, no address available.",
  "latitude": 4.356073157098248,
  "longitude": 139.42454583043394,
  "now_timestamp": "2025-03-13 18:59:05",
  "speed": "7.657886726099852 km/s"
}

``` 
As seen above, this route returned a dictionary with calculated values of altitude, latitude, longitude, speed, and geoposition of the ISS closest to the current time. As you can see, the geoposition has a string that displays "Above a sea, no address available." This is due to the ISS being currently above a sea, where no address exists in the geopy library. 

## Running Test Script 
To run the test script you need to go into the container's shell by following the next steps. 

First of all check the name/container id of your container. 
```bash
docker ps -a 

# Example Output
CONTAINER ID   IMAGE                                       COMMAND                  CREATED         STATUS         PORTS                                       NAMES
8dc00baa459f   rguarneros065/flask-redis-iss_tracker:1.0   "python iss_tracker.…"   2 minutes ago   Up 2 minutes   0.0.0.0:5000->5000/tcp, :::5000->5000/tcp   iss-tracker-flask-app-1
b63a13f92967   redis:7                                     "docker-entrypoint.s…"   2 minutes ago   Up 2 minutes   0.0.0.0:6379->6379/tcp, :::6379->6379/tcp   iss-tracker-redis-db-1
...
```

Now you can run the ```exec``` command with the container id or the name of the flask-redis image. 

```bash 
docker exec -it <Container Name> bash

# Example 
docker exec -it iss-tracker-flask-app-1 bash
```

OR 

```bash 
docker exec -it <Container ID> bash

# Example 
docker exec -it 8dc00baa459f bash
```

```bash 
# Example Output
root@418dbdb69c99:/app# 
```
Now you are inside the container's environment. You are able to run the curl commands as discussed in the [Accessing Microservice](README.md#accessing-microservice) section. Please refer to this sections for further details. 

In addition to running the curl commands, you are also able to run pytest. You should have been initialized into the ```/app``` folder. If you run ```ls``` you should see the iss_tracker and test scripts. To run the pytests you can do the following: 
```bash
pytest

# Example Output
==================================================================== test session starts =====================================================================
platform linux -- Python 3.12.9, pytest-8.3.4, pluggy-1.5.0
rootdir: /app
collected 9 items                                                                                                                                            

test_iss_tracker.py .........                                                                                                                          [100%]

===================================================================== 9 passed in 19.25s =====================================================================
```

You ran 9 tests inside the test_iss_tracker.py script. You are able to take a closer look at these tests using ```cat test_iss_tracker.py```. 

You have successfully ran all the scripts in this folder. To exit the container run: 
```bash 
exit
```
This will bring you back to your system's environment. 

## Clean Up 
Don't forget to stop your running containers and remove them when you are done. All you need to run is: 

```bash 
docker compose down 

# Output
WARN[0000] /home/ubuntu/ISS-Tracker/docker-compose.yml: `version` is obsolete 
[+] Running 3/3
 ✔ Container iss-tracker-flask-app-1  Removed                                                                                                            0.5s 
 ✔ Container iss-tracker-redis-db-1   Removed                                                                                                            0.3s 
 ✔ Network iss-tracker_default        Removed                                                                                                            0.1s 

```

You can double check that you successfully exited and removed the running container by running ```docker ps -a```. You should see that iss-tracker-flask-app-1 and iss-tracker-redis-db-1 are gone. 

## Resources 

* Logging Documentation: https://docs.python.org/3/howto/logging.html
* Requests Library: https://pypi.org/project/requests/ 
* Requests Library Head: https://www.geeksforgeeks.org/head-method-python-requests/ 
* pow() Function: https://www.w3schools.com/python/ref_math_pow.asp 
* ISS Trajectory Data: https://spotthestation.nasa.gov/trajectory_data.cfm 
* COE 332 Spring 2025 Docs: https://coe-332-sp25.readthedocs.io/en/latest/ 
* Table Syntax for README: https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/organizing-information-with-tables 
* time library - https://www.geeksforgeeks.org/python-time-module/ 
* sort library - https://www.geeksforgeeks.org/sort-in-python/ 
* geopy library - https://geopy.readthedocs.io/en/stable/#module-geopy.geocoders 
* astropy library - https://docs.astropy.org/en/stable/index_user_docs.html 

## AI Usage
AI (ChatGPT) was mainly used for debugging the code. Sometimes, my syntax would be wrong and I used AI to help me identify it. Most of the built-in functions used in the scripts were found by reading the documentation cited in [Resources](README#resources). 

ChatGPT was used to make my code more robust since I wanted it to 'spit' out a 404 error code when given a wrong epoch. It was also used to look for the 'Last-Modified' date in the redis database by iterating through the whole dataset. The sections where AI was used are commented appropriately in the code. 

AI was also used to find a way to constantly fetch the latest ISS data. This was done by starting a background updater in a seperate thread. 

## Author(s)
[Richard Guarneros](https://github.com/RGuarneros)