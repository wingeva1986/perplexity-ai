import json
import time
import requests
import random
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
from bs4 import BeautifulSoup
from websocket import WebSocketApp
from uuid import uuid4
from threading import Thread

# utility function for parsing HTML content - using BeautifulSoup
def souper(x):
    return BeautifulSoup(x, 'lxml')

# generate temporary email addresses
class Emailnator:
    def __init__(self, headers, cookies, domain=False, plus=False, dot=True, google_mail=False):
        
        self.inbox = []
        self.inbox_ads = []

        # create session with provided headers & cookies
        self.s = requests.Session()
        self.s.headers.update(headers)
        self.s.cookies.update(cookies)

        # preparing data for email generation
        data = {'email': []}
        if domain:
            data['email'].append('domain')
        if plus:
            data['email'].append('plusGmail')
        if dot:
            data['email'].append('dotGmail')
        if google_mail:
            data['email'].append('googleMail')

        # generate temporary email address
        response = self.s.post('https://www.emailnator.com/generate-email', json=data).json()
        self.email = response['email'][0]

        
        for ads in self.s.post('https://www.emailnator.com/message-list', json={'email': self.email}).json()['messageData']:
            self.inbox_ads.append(ads['messageID'])

    # reload inbox messages
    def reload(self, wait=False, retry_timeout=5):
        self.new_msgs = []

        while True:
            for msg in self.s.post('https://www.emailnator.com/message-list', json={'email': self.email}).json()['messageData']:
                if msg['messageID'] not in self.inbox_ads and msg not in self.inbox:
                    self.new_msgs.append(msg)

            if wait and not self.new_msgs:
                time.sleep(retry_timeout)
            else:
                break

        self.inbox += self.new_msgs
        return self.new_msgs

    # open selected inbox message
    def open(self, msg_id):
        return self.s.post('https://www.emailnator.com/message-list', json={'email': self.email, 'messageID': msg_id}).text

# client class for interactions with perplexity ai webpage
class Client:
    def __init__(self, headers, cookies):
        self.session = requests.Session()
        self.session.headers.update(headers)
        self.session.cookies.update(cookies)
        self.session.get(f'https://www.perplexity.ai/search/{str(uuid4())}')

        # generate random values for session init
        self.t = format(random.getrandbits(32), '08x')
        self.sid = json.loads(self.session.get(f'https://www.perplexity.ai/socket.io/?EIO=4&transport=polling&t={self.t}').text[1:])['sid']
        self.frontend_uuid = str(uuid4())
        self.frontend_session_id = str(uuid4())
        self._last_answer = None
        self._last_file_upload_info = None
        self.copilot = 0
        self.file_upload = 0
        self.n = 1


        assert self.session.post(f'https://www.perplexity.ai/socket.io/?EIO=4&transport=polling&t={self.t}&sid={self.sid}', data='40{"jwt":"anonymous-ask-user"}').text == 'OK'

        # setup websocket comm
        self.ws = WebSocketApp(
            url=f'wss://www.perplexity.ai/socket.io/?EIO=4&transport=websocket&sid={self.sid}',
            cookie='; '.join([f'{x}={y}' for x, y in self.session.cookies.get_dict().items()]),
            header={'user-agent': self.session.headers['user-agent']},
            on_open=lambda ws: ws.send('2probe'),
            on_message=self.on_message,
            on_error=lambda ws, err: print(f'Error: {err}'),
        )

        # start webSocket thread
        Thread(target=self.ws.run_forever).start()
        time.sleep(1)

    # method to create an account on the webpage
    def create_account(self, headers, cookies):
        emailnator_cli = Emailnator(headers, cookies, dot=False, google_mail=True)

        resp = self.session.post('https://www.perplexity.ai/api/auth/signin/email', data={
            'email': emailnator_cli.email,
            'csrfToken': self.session.cookies.get_dict()['next-auth.csrf-token'].split('%')[0],
            'callbackUrl': 'https://www.perplexity.ai/',
            'json': 'true',
        })

        if resp.ok:
            new_msgs = emailnator_cli.reload(wait=True)
            new_account_link = souper(emailnator_cli.open(new_msgs[0]['messageID'])).select('a')[1].get('href')

            self.session.get(new_account_link)
            self.session.get('https://www.perplexity.ai/')

            self.copilot = 5
            self.file_upload = 3

            self.ws.close()

            
            # generate random values for session init
            
            self.t = format(random.getrandbits(32), '08x')
            self.sid = json.loads(self.session.get(f'https://www.perplexity.ai/socket.io/?EIO=4&transport=polling&t={self.t}').text[1:])['sid']

            assert self.session.post(f'https://www.perplexity.ai/socket.io/?EIO=4&transport=polling&t={self.t}&sid={self.sid}', data='40{"jwt":"anonymous-ask-user"}').text == 'OK'

            # reconfig - webSocket communication
            self.ws = WebSocketApp(
                url=f'wss://www.perplexity.ai/socket.io/?EIO=4&transport=websocket&sid={self.sid}',
                cookie='; '.join([f'{x}={y}' for x, y in self.session.cookies.get_dict().items()]),
                header={'user-agent': self.session.headers['user-agent']},
                on_open=lambda ws: ws.send('2probe'),
                on_message=self.on_message,
                on_error=lambda ws, err: print(f'Error: {err}'),
            )

            # start webSocket thread
            Thread(target=self.ws.run_forever).start()
            time.sleep(1)

            return True

    # message handler def
    def on_message(self, ws, message):
        if message == '2':
            ws.send('3')
        elif message == '3probe':
            ws.send('5')

        if message.startswith(str(430 + self.n)):
            response = json.loads(message[3:])[0]

            if 'text' in response:
                response['text'] = json.loads(response['text'])
                self._last_answer = response
            else:
                self._last_file_upload_info = response

    # method to search on the webpage
    def search(self, query, mode='concise', focus='internet', file=None):
        assert mode in ['concise', 'copilot'], 'Search modes --> ["concise", "copilot"]'
        assert focus in ['internet', 'scholar', 'writing', 'wolfram', 'youtube', 'reddit', 'wikipedia'], 'Search focus modes --> ["internet", "scholar", "writing", "wolfram", "youtube", "reddit", "wikipedia"]'
        assert self.copilot > 0 if mode == 'copilot' else True, 'You have used all of your copilots'
        assert self.file_upload > 0 if file else True, 'You have used all of your file uploads'

        self.copilot = self.copilot - 1 if mode == 'copilot' else self.copilot
        self.file_upload = self.file_upload - 1 if file else self.file_upload
        self.n += 1
        self._last_answer = None
        self._last_file_upload_info = None

        if file:
            # request an upload URL for a file
            self.ws.send(f'{420 + self.n}' + json.dumps([
                'get_upload_url',
                {
                    'version': '2.0',
                    'source': 'default',
                    'content_type': {'txt': 'text/plain', 'pdf': 'application/pdf'}[file[1]]
                }
            ]))

            while not self._last_file_upload_info:
                pass

            if not self._last_file_upload_info['success']:
                raise Exception('File upload error', self._last_file_upload_info)

            monitor = MultipartEncoderMonitor(MultipartEncoder(fields={
                **self._last_file_upload_info['fields'],
                'file': ('myfile', file[0], {'txt': 'text/plain', 'pdf': 'application/pdf'}[file[1]])
            }))

            if not (upload_resp := requests.post(self._last_file_upload_info['url'], data=monitor, headers={'Content-Type': monitor.content_type})).ok:
                raise Exception('File upload error', upload_resp)

            uploaded_file = self._last_file_upload_info['url'] + self._last_file_upload_info['fields']['key'].replace('${filename}', 'myfile')

            # send search request with uploaded file as an attachment
            self.ws.send(f'{420 + self.n}' + json.dumps([
                'perplexity_ask',
                query,
                {
                    'attachments': [uploaded_file],
                    'version': '2.0',
                    'source': 'default',
                    'mode': mode,
                    'last_backend_uuid': None,
                    'read_write_token': '',
                    'conversational_enabled': True,
                    'frontend_session_id': self.frontend_session_id,
                    'search_focus': focus,
                    'frontend_uuid': self.frontend_uuid,
                    'gpt4': False,
                    'language': 'en-US',
                }
            ]))
        else:
            # send search request without file attachment
            self.ws.send(f'{420 + self.n}' + json.dumps([
                'perplexity_ask',
                query,
                {
                    'version': '2.0',
                    'source': 'default',
                    'mode': mode,
                    'last_backend_uuid': None,
                    'read_write_token': '',
                    'conversational_enabled': True,
                    'frontend_session_id': self.frontend_session_id,
                    'search_focus': focus,
                    'frontend_uuid': self.frontend_uuid,
                    'gpt4': False,
                    'language': 'en-US',
                }
            ]))

        while not self._last_answer:
            pass

        return self._last_answer
