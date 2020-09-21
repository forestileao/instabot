from os import path
import time
from time import sleep
import requests
import json
from threading import Thread


class InstaBot:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.base_url = 'https://www.instagram.com'


    def get_userid(self, username):
        url = f'https://instagram.com/{username}/?__a=1'
        req = self.session.get(url)

        if req.status_code == 200:
            req = json.loads(req.content.decode('utf-8'))['graphql']['user']
            return req['id']
        else:
            return None


    # Generates a string to use as enc_password during the login request
    def generate_encrypted_password(self):
        str_time = str(int(time.time()))
        return '#PWD_INSTAGRAM_BROWSER:0:' + str_time + ':' + self.password


    def login(self):
        login_url = self.base_url + '/accounts/login/ajax/'
        user_agent = 'Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36'

        #Setting some headers
        self.session = requests.Session()
        self.session.headers = {'user-agent': user_agent}
        self.session.headers.update({'Referer': self.base_url})
        enc_password = self.generate_encrypted_password()

        try:
            #Requesting the base url. Grabbing and inserting the csrftoken
            req = self.session.get(self.base_url)
            self.session.headers.update({'x-csrftoken': req.cookies['csrftoken']})
            login_data = {'username': self.username, 'enc_password': enc_password}

            #Finally login in
            login = self.session.post(login_url, data=login_data, allow_redirects=True)
            self.session.headers.update({'x-csrftoken': login.cookies['csrftoken']})
            login = json.loads(login.content.decode('utf-8'))

            if login['authenticated']:
                self.user_id = login['userId']
                print(f'> Logged in (user:{self.username}, id:{self.user_id})')

            else:
                print('> Erron on login authentication')
                print(login)
            return login

        #In case of refused connection
        except requests.exceptions.ConnectionError:
            print("> Connection refused")


    def map_user_followers(self, username, limit=1000):
        print(f'*** Mapping {limit} followers from {username}***')
        self.user_followers = []
        self.user_foll_num = int(0)
        user_id = self.get_userid(username)
        count = 0
        cursor = ''
        while True:
            foll_url = self.base_url+'/graphql/query/?query_hash=c76146de99bb02f6415203be841dd25a&variables={'+ f'"id":"{user_id}","include_reel":true,"fetch_mutual":true,"first":24'+'}'
            if count == 0:
                foll_req = self.session.get(foll_url)
                foll_req_list = json.loads(foll_req.content.decode('utf-8'))
                self.user_foll_num = foll_req_list["data"]['user']['edge_followed_by']['count']
            else:
                foll_url = self.base_url+'/graphql/query/?query_hash=c76146de99bb02f6415203be841dd25a&variables={'+ f'"id":"{user_id}","include_reel":true,"fetch_mutual":false,"first":12,"after":"{cursor}"'+'}'
                foll_req = self.session.get(foll_url)
                foll_req_list = json.loads(foll_req.content.decode('utf-8'))

            if foll_req_list['status'] == 'fail':
                break

            foll_req_list = foll_req_list['data']['user']['edge_followed_by']
            for user in foll_req_list['edges']:
                if self.verbose:
                    print(f'> {user["node"]["username"]} added to target followers list')
                self.user_followers.append({
                    'username':user['node']['username'],
                    'id':user['node']['id']
                })
                count += 1

            cursor = foll_req_list['page_info']['end_cursor']
            if count == limit:
                with open(path.dirname(__file__)+'/../cache/target-followers.json', 'w') as outfile:
                    json.dump(self.followers, outfile)
                break



    def map_followers(self):
        print('*** Mapping followers ***')
        self.followers = []
        self.foll_num = int(0)
        count = 0
        cursor = ''
        while True:
            foll_url = self.base_url+'/graphql/query/?query_hash=c76146de99bb02f6415203be841dd25a&variables={'+f'"id":"{self.user_id}","include_reel":true,"fetch_mutual":true,"first":24'+'}'
            if count == 0:
                foll_req = self.session.get(foll_url)
                foll_req_list = json.loads(foll_req.content.decode('utf-8'))
                self.foll_num = int(foll_req_list["data"]['user']['edge_followed_by']['count'])
            else:
                foll_url = self.base_url+'/graphql/query/?query_hash=c76146de99bb02f6415203be841dd25a&variables={'+f'"id":"{self.user_id}","include_reel":true,"fetch_mutual":false,"first":12,"after":"{cursor}"'+'}'
                foll_req = self.session.get(foll_url)
                foll_req_list = json.loads(foll_req.content.decode('utf-8'))

            if foll_req_list['status'] == 'fail':
                break

            foll_req_list = foll_req_list['data']['user']['edge_followed_by']
            for user in foll_req_list['edges']:
                self.followers.append({
                    'username':user['node']['username'],
                    'id':user['node']['id']
                })
                count += 1
                if self.verbose:
                    print('>', user['node']['username'], 'added to follower list')

            cursor = foll_req_list['page_info']['end_cursor']
            if count == self.foll_num:
                with open(path.dirname(__file__)+'/../cache/followers.json', 'w') as outfile:
                    json.dump(self.followers, outfile)
                break


    def map_following(self):
        print('*** Mapping people who you are following ***')
        self.following = []
        foll_url = self.base_url+'/graphql/query/?query_hash=d04b0a864b4b54837c0d870b0e77e076&variables={'+f'"id":"{self.user_id}","include_reel":true,"fetch_mutual":true,"first":24'+'}'
        count = 0
        cursor = ''

        while True:
            if count == 0:
                foll_req = self.session.get(foll_url)
                foll_req_list = json.loads(foll_req.content.decode('utf-8'))
                self.following_num = foll_req_list["data"]['user']['edge_follow']['count']
            else:
                foll_url = self.base_url+'/graphql/query/?query_hash=d04b0a864b4b54837c0d870b0e77e076&variables={'+f'"id":"{self.user_id}","include_reel":true,"fetch_mutual":false,"first":24,"after":"{cursor}"'+'}'
                foll_req = self.session.get(foll_url)
                foll_req_list = json.loads(foll_req.content.decode('utf-8'))

            if foll_req_list['status'] == 'fail':
                break

            for user in foll_req_list['data']['user']['edge_follow']['edges']:
                self.following.append({
                    'username':user['node']['username'],
                    'id':user['node']['id']
		})
                count += 1
                if self.verbose:
                    print('>', user['node']['username'], 'added to list of people you are following')

            cursor = foll_req_list['data']['user']['edge_follow']['page_info']['end_cursor']

            if count == self.following_num:
                with open(path.dirname(__file__)+'/../cache/following.json', 'w') as outfile:
                    json.dump(self.following, outfile)
                break


    def follow_user(self, userid):
        url = self.base_url + f'/web/friendships/{userid}/follow/'
        req = self.session.post(url)
        print('['+str(req.status_code)+']', end='')
        if req.content.decode('utf-8')[:3] == 'Ple' or req.status_code != 200:
            return False
        return True


    def unfollow_user(self, userid):
        url = self.base_url + f'/web/friendships/{userid}/unfollow/'
        req = self.session.post(url)
        print('['+str(req.status_code)+']', end='')
        if req.content.decode('utf-8')[:3] == 'Ple' or req.status_code != 200:
            return False
        return True


    def get_suggested_followers(self):
        query = {
            'fetch_media_count': 0,
            'fetch_suggested_count': 30,
            'ignore_cache': True,
            'filter_followed_friends': True,
            'seen_ids': [],
            'include_reel': True
        }

        sug_list = []
        url = self.base_url + '/graphql/query/?query_hash=ed2e3ff5ae8b96717476b62ef06ed8cc&variables=' + json.dumps(query)

        req = self.session.get(url)
        if req.status_code == 200:
            print('> Getting Suggested')
            req = json.loads(req.content.decode('utf-8'))
            print(req['status'])

            for foll in req['data']['user']['edge_suggested_users']['edges']:
                if foll['node']['description'][:3] == 'Ins':
                    continue
                sug_list.append({
                    'username': foll['node']['user']['username'],
                    'id': foll['node']['user']['id']
                })
            return sug_list
        else:
            return None


    def just_follow(self):
        if not self.other_user:
            self.map_followers()
            while self.foll_num < self.hoped_foll or self.other_user:

                print('*** Following Users ***')
                try:
                    for user in self.get_suggested_followers():
                        if self.follow_user(user['id']):
                            print(f'> Followed {user["username"]}')
                        else:
                            print('> Waiting 10 min until next FOLLOW request')
                            sleep(10 * 60)
                except:
                    print('> Error in suggested')
                    sleep(3 * 60)
        else:
            self.map_user_followers(username=self.target_username)
            while self.user_foll_num < self.hoped_foll or self.other_user:
                print('*** Following Users ***')
                try:
                    for user in self.user_followers:
                        if self.follow_user(user['id']):
                            print(f'> Followed {user["username"]}')
                        else:
                            print('> Waiting 10 min until next FOLLOW request')
                            sleep(10 * 60)
                except:
                    print('> Error in suggested')
                    sleep(3 * 60)


    def just_unfollow(self):
        self.map_followers()
        self.map_following()
        while self.following_num > self.foll_num or self.unfollow_all_not_followers:
            print("[*] Followers:", self.foll_num)
            print("[*] Following:", self.following_num)
            for following in self.following:
                count = 1
                if count >= 50:
                    break
                else:
                    if {'username':following['username'], 'id':following['id']} in self.followers:
                        count +=1
                        continue
                    else:
                        while not self.unfollow_user(following['id']):
                            print('> Waiting 10 minutes until next UNFOLLOW request.')
                            sleep(10 * 60)
                        print(f'> Unfollowed {following["username"]}')
            self.map_followers()
            self.map_following()


    def start(self, target_username='', hoped_foll=2000, unfollow_all_not_followers=True, verbose=False):
        #self.init_time = time.gmtime()  Not used yet
        self.unfollow_all_not_followers = unfollow_all_not_followers
        self.other_user = False
        self.verbose = verbose

        if len(target_username) > 0:
            self.target_username = target_username
            self.other_user = True

        self.hoped_foll = hoped_foll
        self.login()

        fol = Thread(target=self.just_follow)
        fol.start()
        unfol = Thread(target=self.just_unfollow)
        unfol.start()
