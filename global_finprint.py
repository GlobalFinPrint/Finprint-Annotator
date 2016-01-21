from config import global_config
import requests
import datetime

class Singleton:
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state


class GlobalFinPrintServer(Singleton):
    def __init__(self):
        Singleton.__init__(self)

        ## Warning... Do not initialize private attributes after it's been instantiated.
        if not hasattr(self, 'instantiated'):
            self.instantiated = True
            self.logged_in = False
            self.user_token = None
            self.user_name = ''
            self.address = global_config.parser['GLOBAL_FINPRINT_SERVER'].get('address')


    def login(self, user_name, pwd):
        data = {'username': user_name, 'password': pwd}
        r = requests.post(self.address + '/api/login', data)
        self.logged_in = False
        data = {}
        if r.status_code == 200:
            self.logged_in = True
            data = r.json()
            self.user_token = data['token']
            self.user_name = user_name
        elif r.status_code == 403:
            data['msg'] = 'Unknown User'
        else:
            data['msg'] = 'Unknown status code ' + r.status_code

        return self.logged_in, data

    def logout(self):
        r = requests.post(self.address + '/api/logout', {'token': self.user_token})
        self.logged_in = r.status_code == 200
        return self.logged_in

    def set_list(self):
        r = requests.get(self.address + '/api/set', params={'token': self.user_token})
        return r.json()

    def set_detail(self, set_id):
        r = requests.get(self.address + '/api/set/{0}'.format(set_id), params={'token': self.user_token})
        return r.json()

    def mark_set_done(self, set_id):
        r = requests.post(self.address + '/api/set/{0}/done'.format(set_id), {'token': self.user_token})
        return r.status_code == 200

    def observations(self, set_id):
        r = requests.get(self.address + '/api/set/{0}/obs'.format(set_id), params={'token': self.user_token})
        return r.json()

    def add_observation(self, set_id, observation):
        data = observation.to_dict()
        data['token'] = self.user_token
        r = requests.post(self.address + '/api/set/{0}/obs'.format(set_id), data)
        if r.status_code == 200:
            return r.json()

    def delete_observation(self, set_id, obs_id):
        r = requests.delete(self.address + '/api/set/{0}/obs'.format(set_id), params={'obs_id': obs_id, 'token': self.user_token})
        if r.status_code == 200:
            return r.json()

    def critters(self, set_id):
        r = requests.get(self.address + '/api/set/{0}/critters'.format(set_id), params={'token': self.user_token})
        return r.json


class Observation(object):
    def __init__(self):
        self.position = 0
        self.initial_observation_time = datetime.datetime.now()
        self.animal_id = None
        self.behavior_id = None
        self.comment = ''
        self.duration = 0
        self.animal = ''

    def load(self, obs_dict):
        self.id = obs_dict['id']
        self.animal = obs_dict['animal']
        self.comment = obs_dict['comment']
        self.initial_observation_time = datetime.datetime.strptime(obs_dict['initial_observation_time'], "%Y-%m-%dT%I:%M:%S.%fZ")


    def to_dict(self):
        return {'initial_observation_time': self.initial_observation_time,
                'animal_id': self.animal_id,
                'behavior_id': self.behavior_id,
                'comment': self.comment,
                'position': self.position,
                'duration': self.duration}


class Set(object):
    def __init__(self, id):
        self._connection = GlobalFinPrintServer()
        self.id = None
        self.file = ''
        self.animals = []
        self.observations = []

        if id is not None:
            data = self._connection.set_detail(id)
            self.id = data['set']['id']
            self.file = data['set']['file']
            self.animals = data['set']['animals']
            for obs in data['set']['observations']:
                o = Observation()
                o.load(obs)
                self.observations.append(o)

    def add_observation(self, obs):
        self._connection.add_observation(self.id, obs)
        a = self.get_animal(obs.animal_id)
        obs.animal = a.animal

    def delete_observation(self, obs):
        self._connection.delete_observation(self.id, obs.id)

    def get_animal(self, id):
        a =(animal for animal in self.animals if animal['id'] == id).next()
        if a:
            return a
        return None
