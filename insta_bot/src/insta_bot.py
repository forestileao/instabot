from os import path
import time
import requests
import json


class InstaBot:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.base_url = 'https://www.instagram.com'


    def get_userid(self, user):
        user_url = f'https://instagram.com/{user}/?__a=1'
        req = self.session.get(user_url)
        if req.status_code == 200:
            req = json.loads(req.content.decode('utf-8'))['graphql']['user']
            return req['id']
        else:
            return None


    def generate_encrypted_password(self):
        str_time = str(int(time.time()))
        return '#PWD_INSTAGRAM_BROWSER:0:' + str_time + ':' + self.password


    def login(self):
        login_url = self.base_url + '/accounts/login/ajax/'
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko)\
            Chrome/59.0.3071.115 Safari/537.36'

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
            return login

        #In case of refused connection
        except requests.exceptions.ConnectionError:
            print("> Connection refused")


    def map_followers(self):
        print('*** Mapping followers ***')
        self.followers = []
        foll_url = self.base_url+'/graphql/query/?query_hash=c76146de99bb02f6415203be841dd25a&variables={'+f'"id":"{self.user_id}","include_reel":true,"fetch_mutual":true,"first":24'+'}'
        count = 0
        cursor = ''

        while True:
            if count == 0:
                foll_req = self.session.get(foll_url)
                foll_req_list = json.loads(foll_req.content.decode('utf-8'))
                self.foll_num = foll_req_list["data"]['user']['edge_followed_by']['count']
            else:
                foll_url = self.base_url+'/graphql/query/?query_hash=c76146de99bb02f6415203be841dd25a&variables={'+f'"id":"{self.user_id}","include_reel":true,"fetch_mutual":false,"first":12,"after":"{cursor}"'+'}'
                foll_req = self.session.get(foll_url)
                foll_req_list = json.loads(foll_req.content.decode('utf-8'))

            foll_req_list = foll_req_list['data']['user']['edge_followed_by']
            for user in foll_req_list['edges']:
                self.followers.append({
                    'username':user['node']['username'],
                    'id':user['node']['id']
		})
                count += 1
                print('>', user['node']['username'], 'added')

            cursor = foll_req_list['page_info']['end_cursor']
            if count == self.foll_num:
                with open(path.dirname(__file__)+'/followers.json', 'w') as outfile:
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
                foll_url = self.base_url+'/graphql/query/?query_hash=d04b0a864b4b54837c0d870b0e77e076&variables={'+f'"id":"{self.user_id}","include_reel":true,"fetch_mutual":false,"first":12,"after":"{cursor}"'+'}'
                foll_req = self.session.get(foll_url)
                foll_req_list = json.loads(foll_req.content.decode('utf-8'))

            foll_req_list = foll_req_list['data']['user']['edge_follow']
            for user in foll_req_list['edges']:
                self.following.append({
                    'username':user['node']['username'],
                    'id':user['node']['id']
		})
                count += 1
                print('>', user['node']['username'], 'added')

            cursor = foll_req_list['page_info']['end_cursor']
            if count == self.following_num:
                with open(path.dirname(__file__)+'/following.json', 'w') as outfile:
                    json.dump(self.followers, outfile)
                break


    def follow_user(self, userid):
        url = self.base_url + f'/web/friendships/{userid}/follow/'
        self.session.post(url)


    def unfollow_user(self, userid):
        url = self.base_url + f'/web/friendships/{userid}/unfollow/'
        self.session.post(url)


    def get_suggested_followers(self):
        query = {
            'fetch_media_count': 0,
            'fetch_suggested_count': 50,
            'ignore_cache': True,
            'filter_followed_friends': True,
            'seen_ids': [],
            'include_reel': True
        }
        sug_list = []
        url = self.base_url + '/graphql/query/?query_hash=ed2e3ff5ae8b96717476b62ef06ed8cc&variables=' + json.dumps(query)

        req = self.session.get(url)
        if req.status_code == 200:
            req = json.loads(req.content.decode('utf-8'))

            for foll in req['data']['user']['edge_suggested_users']['edges']:
                if foll['node']['description'][:3] in ['Fol', 'Sug']:
                    sug_list.append({
                        'username': foll['node']['user']['username'],
                        'id': foll['node']['user']['id']
                    })
            return sug_list
        else:
            return None


    def is_time(self): # Checks if it's time to unfollow initialize unfollowing
        gen_time = time.gmtime()
        hour = gm_time.tm_hour - self.init_time.tm_hour
        minutes =  gen_time.tm_min - self.init_time.tm_min
        if hour < 0:
            hour += 24
            hour *= 60
        else:
            hour *= 60

        if minutes < 0:
            minutes +=60

        total_min = hour + minutes
        if total_min >= 60: # Here, the number represents he time chosen to start the process
            return True
        return False


    def start(self):
        self.init_time = time.gmtime()
        while True:
            print('*** Following Users ***')
            for i in range(3):
                for user in self.get_suggested_followers():
                    try:
                        self.follow_user(user['id'])
                        print(f'> Followed {user["username"]}')
                    except:
                        print('*** Ocurred an Error while tring to follow users ***')
                        print('> Waiting 30 seconds until next request')
                        sleep(30)
                        break
            if self.is_time():
                self.init_time = time.gmtime()
                print('\n-=-=-=-=-= Time to Unfollow who is not following you -=-=-=-=-=')
                self.map_followers()
                self.map_following()
                for count, user in enumerate(self.following):
                    for foll in self.followers:
                        if user['username'] == foll['username']:
                            break
                        elif count+1 == self.following_num:
                            try:
                                self.unfollow_user(user['id'])
                                print(f'> {user["username"]} was unfollowed')
                            except:
                                print(f'> ERROR while tring to unfollow {user["username"]}, waiting 30s until next request.')
                                sleep(30)

