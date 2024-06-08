from collections import defaultdict
from flask import Flask, jsonify
import geopy.distance
import pandas as pd
import sqlite3
import os

app = Flask(__name__)

@app.before_first_request
def initialize_database():
    # Read in the dataset
    basedir = os.path.abspath(os.path.dirname(__file__))
    file = os.path.join(basedir, 'static/cities_canada-usa.tsv')
    cities = pd.read_table(file)
    
    # Store it in a local database with sqlite3
    con = sqlite3.connect('cities.db', check_same_thread=False)
    cities.to_sql(name='cities', con=con, if_exists="replace")
    
# Handle optional latitude and longitude parameters with two different routes
@app.route('/suggestions/<q>', methods=['GET'], defaults={'latitude': None, 'longitude': None})
@app.route('/suggestions/<q>/<latitude>/<longitude>', methods=['GET'])
def suggestions(q, latitude, longitude):    
    # Read matching cities from the database
    query = 'SELECT name, country, admin1, lat, long \
             FROM cities \
             WHERE name LIKE "{}%"'.format(q)
    con = sqlite3.connect('cities.db', check_same_thread=False)
    cities = pd.read_sql(query, con)

    distance_provided = latitude and longitude
    distance_map, similarity_map = defaultdict(float), {}
    suggestions = {}
    for _, city in cities.iterrows():
        # Populate the suggested cities information minus the score
        unique_name = ", ".join([city["name"], city["admin1"], city["country"]])
        suggestions[unique_name] = {"name": unique_name, "latitude": city["lat"], "longitude": city["long"]}
        
        # Calculate the jaccard similarity index and store it in similarity_map
        similarity_score = jaccard_similarity(q, city["name"])
        similarity_map[unique_name] = similarity_score

        # If latitude and longitude were provided, calculate the distance
        # and store it in the distance_map
        if distance_provided:
            similarity_map[unique_name] /= 2 # similarity counts as half of the score if distance is provided
            local, candidate = (latitude, longitude), (city["lat"], city["long"])
            distance = geopy.distance.geodesic(local, candidate)
            distance_map[unique_name] = distance.km
    
    # With all distances calculated, normallize the distances and reduce them
    # by half to account for the similarity score
    if distance_provided:
        distance_sum = sum(distance_map.values())
        for key, distance in distance_map.items():
            distance_map[key] = (distance /distance_sum) / 2
    
    # Add the similarity and distance calculations (if lat/long provided)
    result = {"suggestions": []}
    for city in suggestions.keys():
        total_score = similarity_map[city] + distance_map[city]
        suggestions[city]["score"] = round(total_score, 1)
    result["suggestions"] = sorted(suggestions.values(), key=lambda val: val["score"], reverse=True)

    return jsonify(result)

# Jaccard similarity calculates the similarity between two strings
# based on the following formula: 
#     J(A, B) = |A intersection B| / |A Union B|
# Scikit Learn has a metric for calculating Jaccard similarity, but
# it's simple enough to compute locally and save ourselves a dependency
def jaccard_similarity(string1, string2):
    set1, set2 = set(string1), set(string2)
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union

if __name__== '__main__':
    app.run()