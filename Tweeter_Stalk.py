from robobrowser import RoboBrowser
import requests
from bs4 import BeautifulSoup
import random
from geotext import GeoText
from geopy.geocoders import Nominatim
from tqdm import tqdm_notebook as tqdm
#from tqdm as tqdm
import matplotlib.pyplot as plt
import tweepy
from tweepy import OAuthHandler
import pandas as pd
import json as json

class twitter_stalker:
    
    def __init__(self ):

        self.HEADERS_LIST = [
        'Mozilla/5.0 (Windows; U; Windows NT 6.1; x64; fr; rv:1.9.2.13) Gecko/20101203 Firebird/3.6.13',
        'Mozilla/5.0 (compatible, MSIE 11, Windows NT 6.3; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (Windows; U; Windows NT 6.1; rv:2.2) Gecko/20110201',
        'Opera/9.80 (X11; Linux i686; Ubuntu/14.10) Presto/2.12.388 Version/12.16',
        'Mozilla/5.0 (Windows NT 5.2; RW; rv:7.0a1) Gecko/20091211 SeaMonkey/9.23a1pre'
        ]
        self.session = requests.Session()
        self.browser = RoboBrowser(session=self.session, user_agent=random.choice(self.HEADERS_LIST))
        self.handle = ''
        self.id_url = "https://twitter.com/intent/user?user_id="
        self.prof_url = "https://twitter.com/"
        self.TWITTER_AUTH = tweepy.OAuthHandler(
            "",
            ""
        )
        self.TWITTER_AUTH.set_access_token(
            "",
            ""
        )
        self.api = tweepy.API(self.TWITTER_AUTH, parser = tweepy.parsers.JSONParser(), wait_on_rate_limit = True, wait_on_rate_limit_notify = True, compression=True)

    def get_ids(self, user):
        followers = []
        p = self.api.followers_ids(user)
        followers.extend(p['ids'])
        return followers
    
    def get_id(self, user):
        p = self.api.get_user("sydshelby")
        if p == None:
            print("Couldn't get user ID from user_name")
            return None
        return p['id']

    def get_handle(self, id):  # Takes an id number and returns screenname
        url = self.id_url+str(id)
        self.browser.open(url)
        results = self.browser.find_all("span", {"class": "nickname"})
        try:
            handle = (" ".join(str(results[0].text).split()))
            return handle
        except (IndexError):
            return None

    def get_loc(self, screen_name): # takes a screen name and tries to return location from bio
        url = "https://twitter.com/" + str(screen_name) 
        self.browser.open(url)
        try:
            results = self.browser.find_all("span", {"class": "ProfileHeaderCard-locationText u-dir"})
            handle = (" ".join(str(results[0].text).split()))
            if handle.isspace() or handle == None or not handle:
                return None
            return (" ".join(str(results[0].text).split()))
        except (IndexError):
            return None
        
    def normalize_cities(self, document):
        places = GeoText(document)
        try:
            return places.cities[0]
        except IndexError:
            return None
        
    def lower_bois(self, document):
        return document.lower()
    
    def get_long_lang(self, document):
        try:
            geolocator = Nominatim(user_agent='myapplication')
            location = geolocator.geocode(document)
            return str(location.raw['lon']),str(location.raw['lat'])
        except:
            return None, None
        
        
    def find_location(self, document):
        handle = None
        location  = None
        user_id = None
        if isinstance(document, int):
            handle = self.get_handle(document)
            user_id = document
            if handle == None:
                print("Couldn't Retrieve Handle through ID, Check ID")
                return
            
        if isinstance(document, str):
            handle = document
        
        location = self.get_loc(handle)
        if location != None:
            std_location = self.normalize_cities(location)
            if std_location == None:
                print("Couldn't Standardize")
                return location
            
        if location == None and user_id != None:
            df = self.process_dict(self.get_id_location(self.get_ids(user_id), 400))
            return self.get_max_df(df)
        
        
        if location == None and user_id == None:
            user_id = self.get_id(handle)
            if user_id != None:
                df = self.process_dict(self.get_id_location(self.get_ids(user_id), 400))
                return self.get_max_df(df)
            return None

    def get_people(self, link, handle):
        session = requests.Session()
        people_list = []
        browser = RoboBrowser(session=session, user_agent=random.choice(self.HEADERS_LIST), parser="lxml")
        url = "https://twitter.com" + link
        try:
            browser.open(url)
            results = browser.find_all("a", {
                "class": "account-group js-account-group js-action-profile js-user-profile-link js-nav"})
            for link in results:
                people_list.append(str(link.get('href')).replace("/", ""))
        except:
            pass
        return people_list

    def get_tweets(self, handle, max_position=None):
        session = requests.Session()
        browser = RoboBrowser(session=session, user_agent=random.choice(self.HEADERS_LIST), parser="lxml")

        url = "https://twitter.com/i/profiles/show/" + handle + "/timeline/tweets?include_available_features=false&include_entities=false&reset_error_state=false"
        if max_position != None:
            url = url + "&" + "max_position=" + max_position
        browser.open(url)
        result = json.loads(browser.response.content)
        min_position = result['min_position']
        soup = BeautifulSoup(result['items_html'], 'lxml')
        links = []
        for link in soup.find_all('a'):
            if str("/" + handle + "/status/").lower() in str(link).lower():
                links.append(link.get('href'))
        return min_position, links


    def duplicates(self, duplicate): 
        final_list = [] 
        for num in duplicate: 
            if num not in final_list: 
                final_list.append(num) 
        return final_list 
    
    def Non_Tweep_friends(self, handle):
        min_position, links = self.get_tweets(handle)
        while (True):
            min_position1, links1 = self.get_tweets(handle, min_position)
            links = links + links1
            if (min_position1 == None):
                break
            min_position = min_position1

        people_list = []

        for link in tqdm(links):
            if handle in link:
                people_list = people_list + self.get_people(link, handle)
                people_list = self.duplicates(people_list)
            people_list = self.duplicates(people_list)

        return(people_list)
        
    def get_max_df(self, df):
        max = -1
        name = ""
        for index, row in df.iterrows():
            if max < row['Counts']:
                max = row['Counts']
                name = row['norm_locations']
        if name == "":
            print("ERROR bad df")
            return None
        return name
            
            
    def get_id_location(self, followers_ids, amount): #takes list of follower ids returns dict of location frequencies
        locations = {}
        j = 0
        for i in tqdm(followers_ids):
            place = self.get_handle(str(i))
            if(place == None):
                continue
            place = self.get_loc(place)
            
            if(place == None):
                continue    
            if place not in locations:
                locations[place] = 0
            locations[place]  = locations[place] +1
            j = j+1
            if (j>amount):
                break
        return locations
    
    def get_followers_location(self, followers_ids, amount): #takes list of screen names returns dict of location counts
        locations = {}
        j = 0
        for i in tqdm(followers_ids):
            place = self.get_loc(i)
            if(place == None):
                continue    
            if place not in locations:
                locations[place] = 0
            locations[place]  = locations[place] +1
            j = j+1
            if (j>amount):
                break
        return locations

    def process_dict(self, locations):
        s = pd.Series(locations, name='Counts')
        s.index.name = 'Locations'
        s = s.reset_index()
        #s = s[s.Counts > 1]
        s = s[s.Locations != '']
        s["norm_locations"] = s.Locations.apply(self.normalize_cities)
        s["norm_locations"].fillna(s.Locations, inplace=True) 
        s["norm_locations"] = s["norm_locations"].apply(self.lower_bois)
        s = s.groupby(s.norm_locations).sum()
        s.sort_values(by=['Counts'])
        s = s.reset_index()
        s["longlat"] = s.norm_locations.apply(self.get_long_lang)
        s['long'] = s['longlat'].str[0]
        s['lat'] = s['longlat'].str[1]
        return s
