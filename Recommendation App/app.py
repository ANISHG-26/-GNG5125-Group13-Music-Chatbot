from flask import Flask, jsonify, request
import re
import urllib.request
import urllib.parse
import pandas as pd
import random

import recommendation

# initialize our Flask application
app = Flask(__name__)


#Function for recommending other songs by a given artist
def songByArtist(content):
  artist = content['queryResult']['parameters']['music-artist'].lower()

  rec_list = recommendation.get_popular_songs(artist)
  
  if len(rec_list) > 0:
    if len(rec_list) > 5:
      rec_list = rec_list[:5]  #suggest only 5 songs
    msg = "Here are a few of the popular songs by " + artist.title() + " \n"
    for s in rec_list:
      msg += ", " + s

  else:  #if we don't know the artist
    msg = "I don't have any suggestions for this artist, sorry!"

  fulfilment_response = {"fulfillmentMessages": [{"text": {"text": [msg]}}]}
  return jsonify(fulfilment_response)


#Function for recommending popular song by artist
def popularSong(content):
  artist = content['queryResult']['parameters']['music-artist'].lower()
  rec_list = recommendation.get_popular_songs(artist)

  if len(rec_list) > 0:
    msg = rec_list[0] + " is one of the popular songs by " + artist.title() 


  else:
    msg = "I'm sorry, I haven't heard of that artist."

  fulfilment_response = {"fulfillmentMessages": [{"text": {"text": [msg]}}]}
  return jsonify(fulfilment_response)


#Function for recommending song by genre
def songByGenre(content):
  genre = content['queryResult']['parameters']['music-genre'][0].lower()

  rec_list = recommendation.get_song_by_genre(genre)
  response_string = ""
  if len(rec_list) > 0:
    response_string += "Here are some songs in the " + genre + " genre \n"

  
    for rec in rec_list:
      response_string += rec['name'] + " by " + rec['artists'].replace(
        "[", "").replace("]", "").replace("'", "") + " (" + str(
          rec['year']) + "), \n"

  else:
    response_string += "Sorry, I don't have any recommendations for you in that genre."

  fulfilment_response = {
    "fulfillmentMessages": [{
      "text": {
        "text": [response_string]
      }
    }]
  }
  return jsonify(fulfilment_response)


#Function for recommending albums by artist
def getAlbum(content):
  artist = content['queryResult']['parameters']['music-artist'].lower()
  albums_by_artist = recommendation.get_spotify_artist_albums(artist)
  msg = ""

  if len(albums_by_artist) > 0:
    random.shuffle(albums_by_artist)
    albums = []

    for r in albums_by_artist:
      if len(albums_by_artist) > 3 and len(
          albums
      ) < 3:  #for artists with more than 3 albums, list out just 3 albums
        albums.append(r)  #to get the list in the correct format
      elif len(albums_by_artist) < 3:  #for artists with less than 3 albums
        albums.append(r)

    if len(albums) > 0:  #if we know any albums by the artist
      msg = "Here are a few albums by " + artist.title()
      for i in albums:
        msg += ", " + i

  else:  #if we don't know the artist
    msg = "I don't have any suggestions for this artist, sorry!"

  fulfilment_response = {"fulfillmentMessages": [{"text": {"text": [msg]}}]}
  return jsonify(fulfilment_response)


#Function for getting YT link of a song
def getYTLink(content):
  track = content['queryResult']['parameters']['name_song'].lower().replace(
    "\\", "").replace('\"', '')
  artist = content['queryResult']['parameters']['music-artist'].lower()
  input = urllib.parse.urlencode({'search_query': track + ' by ' + artist})
  html = urllib.request.urlopen("http://www.youtube.com/results?" + input)
  try:
    video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
    fulfilment_response = {
      "fulfillmentMessages": [{
        "text": {
          "text": [
            "Sure, here is the link to the music video for " + track.title() +
            " by " + artist.title() + "\n\n" +
            "https://www.youtube.com/watch?v=" + video_ids[0]
          ]
        }
      }]
    }
    return jsonify(fulfilment_response)
  except:
    fulfilment_response = {
      "fulfillmentMessages": [{
        "text": {
          "text": [
            "Sorry, I couldn't find that song on YouTube. Try again with a different song or artist"
          ]
        }
      }]
    }
    return jsonify(fulfilment_response)


def getRecommendation(content):
  track = content['queryResult']['parameters']['name_song'].lower().replace(
    "\\", "").replace('\"', '')
  artist = content['queryResult']['parameters']['artist'].lower()

  data = pd.read_csv('clustered_song_data.csv')

  song_list = []
  song_dict = {'name': track, 'artist': artist}
  song_list.append(
    song_dict
  )  #request is in the format recommend_songs([{'name': 'despacito', 'artist':'Luis Fonsi'}] ,data)

  list_of_recs = recommendation.recommend_songs(song_list, data, n_songs=6)

  response_string = "Here are some songs similar to " + track.title(
  ) + " by " + artist.title() + ": \n"

  
  for rec in list_of_recs:
    if rec['name'].lower() == track or track in rec['name'].lower():
      continue
    response_string += rec['name'] + " by " + rec['artists'].replace(
      "[", "").replace("]", "").replace("'", "") + " (" + str(
        rec['year']) + "), \n"

  fulfilment_response = {
      "fulfillmentMessages": [{
        "text": {
          "text": [response_string]
        }
      }]
    }
  return jsonify(fulfilment_response)


@app.route('/')
@app.route('/home')
def home():
  return "App is running"


@app.route('/redirect', methods=["POST"])
def redirectToURLs():
  content = request.json
  intent = content['queryResult']['intent']['displayName'].lower()
  resp = {}
  if intent == 'youtube link':
    resp = getYTLink(content)
  elif intent == 'songbyartist':
    resp = songByArtist(content)
  elif intent == 'popular-song':
    resp = popularSong(content)
  elif intent == 'genres':
    resp = songByGenre(content)
  elif intent == 'mood':
    resp = songByMood(content)
  elif intent == 'album':
    resp = getAlbum(content)
  elif intent == 'similar_song':
    resp = getRecommendation(content)
  return resp


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5000)
