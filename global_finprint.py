from config import global_config
import requests
import datetime

class QueryException(Exception):
    pass

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
            self.address = global_config.get('GLOBAL_FINPRINT_SERVER', 'address')

    def login(self, user_name, pwd):
        data = {'username': user_name, 'password': pwd}
        r = requests.post(self.address + '/api/login', data)
        self.logged_in = False
        if r.status_code == 200:
            self.logged_in = True
            data = r.json()
            self.user_token = data['token']
            self.user_name = user_name
        elif r.status_code == 403:
            raise QueryException('Unknown user or user not assigned to proper role')
        else:
            raise QueryException('Unknown status code ' + r.status_code)

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
        else:
            raise QueryException('Failed to add Observation: status {0}'.format(r.status_code))

    def delete_observation(self, set_id, obs_id):
        r = requests.delete(self.address + '/api/set/{0}/obs'.format(set_id), params={'obs_id': obs_id, 'token': self.user_token})
        if r.status_code == 200:
            return r.json()
        else:
            raise QueryException('Failed to delete observation: status {0}'.format(r.status_code))

    def critters(self, set_id):
        r = requests.get(self.address + '/api/set/{0}/critters'.format(set_id), params={'token': self.user_token})
        return r.json


class Animal(object):
    def __init__(self):
        self._animal_dict = None
        self.id = None
        self.group = None
        self.group_id = 0
        self.rank = 0
        self.genus = ''
        self.species = ''
        self.common_name = 'Unspecified'
        self.sealifebase_key = None
        self.fishbase_key = None
        self.family = None

    def load(self, animal_dict):
        self._animal_dict = animal_dict
        self.id = animal_dict['id']
        self.group = animal_dict['group']
        self.rank = animal_dict['rank']
        self.genus = animal_dict['genus']
        self.species = animal_dict['species']
        self.common_name = animal_dict['common_name']
        self.sealifebase_key = animal_dict['sealifebase_key']
        self.fishbase_key = animal_dict['fishbase_key']
        self.family = animal_dict['family']

    def __str__(self):
        return "{0} ({1} {2})".format(self.common_name, self.genus, self.species)

class Observation(object):
    def __init__(self):
        self.id = None
        self.initial_observation_time = 0
        self.animal_id = None
        self.behavior_id = None
        self.comment = ''
        self.duration = 0
        self.animal = ''

    def load(self, obs_dict):
        self.id = obs_dict['id']
        self.animal_id = obs_dict['animal_id']
        self.comment = obs_dict['comment']
        self.initial_observation_time = int(obs_dict['initial_observation_time'])

    def to_dict(self):
        return {'initial_observation_time': self.initial_observation_time,
                'animal_id': self.animal_id,
                'behavior_id': self.behavior_id,
                'comment': self.comment,
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
            self.animals = []
            for animal in data['set']['animals']:
                a = Animal()
                a.load(animal)
                self.animals.append(a)

            for obs in data['set']['observations']:
                o = Observation()
                o.load(obs)
                self.observations.append(o)

            #Don't like this.  Do something better in the future
            for o in self.observations:
                if o.animal_id is not None:
                    o.animal = self.get_animal(o.animal_id)

    def add_observation(self, obs):
        result = self._connection.add_observation(self.id, obs)
        obs.id = result['observations'][0]['id']
        obs.animal = Animal()
        if obs.animal_id is not None:
            obs.animal = self.get_animal(obs.animal_id)
        self.observations.append(obs)

    def delete_observation(self, obs):
        self._connection.delete_observation(self.id, obs.id)

    def get_animal(self, id):
        a = [animal for animal in self.animals if animal.id == id]
        if len(a):
            return a[0]
        return None


