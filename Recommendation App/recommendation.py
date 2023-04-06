import os
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from sklearn.metrics import euclidean_distances
from scipy.spatial.distance import cdist
from collections import defaultdict
import difflib
import random

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from collections import defaultdict
from spotipy.oauth2 import SpotifyOAuth
import joblib
from decouple import config

import warnings
warnings.filterwarnings("ignore")



loaded_clf_model = joblib.load('joblibed_clf_model.sav')
loaded_cluster_model=joblib.load('joblibed_clust_model.sav')
data = pd.read_csv('clustered_song_data.csv')
number_cols = ['valence', 'year', 'acousticness', 'danceability', 'duration_ms', 'energy', 'explicit',
 'instrumentalness', 'key', 'liveness', 'loudness', 'mode', 'popularity', 'speechiness', 'tempo']
  

def spotifyAuth():
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=config('CLIENT_ID'), client_secret=config('CLIENT_SECRET')))
    return sp


def find_song(name, artist):
    sp = spotifyAuth()
    song_data = defaultdict()
    results = sp.search(q= 'track: {} artist: {}'.format(name,artist), limit=1)
    if results['tracks']['items'] == []:
        return None

    results = results['tracks']['items'][0]
    track_id = results['id']
    audio_features = sp.audio_features(track_id)[0]

    song_data['name'] = [name]
    song_data['artist'] = [artist]
    song_data['year'] = int(results['album']['release_date'][:4])
    song_data['explicit'] = [int(results['explicit'])]
    song_data['duration_ms'] = [results['duration_ms']]
    song_data['popularity'] = [results['popularity']]

    for key, value in audio_features.items():
        song_data[key] = value

    return pd.DataFrame(song_data)


def get_song_data(song, spotify_data):
    
    try:
        song_data = spotify_data[(spotify_data['name'] == song['name']) 
                                & (spotify_data['artists'] == song['artist'])].iloc[0]
        return song_data
    
    except IndexError:
        return find_song(song['name'], song['artist'])
        

def get_mean_vector(song_list, spotify_data):
    
    song_vectors = []
    
    for song in song_list:
        song_data = get_song_data(song, spotify_data)
        if song_data is None:
            print('Warning: {} does not exist in Spotify or in database'.format(song['name']))
            continue
        song_vector = song_data[number_cols].values
        song_vectors.append(song_vector)  
    
    song_matrix = np.array(list(song_vectors))
    return np.mean(song_matrix, axis=0)


def flatten_dict_list(dict_list):
    
    flattened_dict = defaultdict()
    for key in dict_list[0].keys():
        flattened_dict[key] = []
    
    for dictionary in dict_list:
        for key, value in dictionary.items():
            flattened_dict[key].append(value)
            
    return flattened_dict


def recommend_songs( song_list, spotify_data, n_songs=10):
    
    metadata_cols = ['name', 'year', 'artists']
    song_dict = flatten_dict_list(song_list)
    
    song_center = get_mean_vector(song_list, spotify_data)

    #predicting the cluster group the song belongs to
    clust=loaded_clf_model.predict(song_center.reshape(1, -1))

    # slicing the song dataframe to only the cluster predicted
    clust_group=spotify_data.loc[spotify_data['cluster_label'] == int(clust)]

    #scaling the data frame
    scaler = loaded_cluster_model.steps[0][1]
    scaled_data = scaler.transform(clust_group[number_cols])
    scaled_song_center = scaler.transform(song_center.reshape(1, -1))


    # using cdist to find top 10 songs that are similar to the requested song
    distances = cdist(scaled_song_center, scaled_data, 'cosine') 
    index = list(np.argsort(distances)[:, :n_songs][0])
    
    rec_songs = clust_group.iloc[index]
    rec_songs = rec_songs[~rec_songs['name'].isin(song_dict['name'])]
    return rec_songs[metadata_cols].to_dict(orient='records')




#used for the get album by artist intent
def get_spotify_artist_albums(artist):
  sp = spotifyAuth()
  search_res = sp.search(artist + " albums")["tracks"][
    "items"]  #query spotify api for top albums by artist
  album_list = []
  for i in range(len(search_res)):
    album_name = search_res[i]["album"]["name"]
    if album_name not in album_list:  #prevent duplicate results
      album_list.append(album_name)

    return album_list


#used for the genre intent
def get_song_by_genre(genre):
  sp = spotifyAuth()
  search_res = sp.search(genre + " songs")["tracks"][
    "items"]  #query spotify api 
  i = random.randint(0, 10)  #pick a random song from the results
  query_str = {
    "name": search_res[i]["name"],
    "artist": search_res[i]["artists"][0]["name"]
  }  #extract the song name and artist name
  return recommend_songs(
    [query_str], data,
    n_songs=3)  #pass the query to clustering recommendation system



#used for popular songs, as well as songs by artist intent
def get_popular_songs(artist):
  sp = spotifyAuth()
  search_res = sp.search(artist + " top songs")["tracks"]["items"]  #query spotify api 
  
  song_list = []
  for i in range(0,8):  #margin for duplicates
    name = search_res[i]["name"]
    if name not in song_list:
      song_list.append(name)
  
  return song_list  
