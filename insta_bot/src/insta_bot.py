from time import time
import requests
import base64
import json



class InstaBot:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.base_url = 'https://www.instagram.com'
   

    def generate_encrypted_password(self):
        str_time = str(int(time()))
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
                print(f'> Logged in (user:{self.username})')
            else:
                print('> Erron on login authentication')
            return login

        #In case of refused connection
        except requests.exceptions.ConnectionError:
            print("> Connection refused")

