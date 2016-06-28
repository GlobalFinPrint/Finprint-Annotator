from .animal import Animal
from .global_finprint_server import GlobalFinPrintServer
from .observation import Observation


class Set(object):
    def __init__(self, id):
        self._connection = GlobalFinPrintServer()
        self.id = None
        self.file = ''
        self.animals = []
        self.observations = []
        self.attributes = []
        self.code = ''

        if id is not None:
            data = self._connection.set_detail(id)
            self.id = data['set']['id']
            self.file = data['set']['file']
            self.code = data['set']['set_code']
            self.assigned_to = data['set']['assigned_to']
            self.progress = data['set']['progress']
            self.animals = []
            for animal in data['set']['animals']:
                a = Animal()
                a.load(animal)
                self.animals.append(a)

            for obs in data['set']['observations']:
                o = Observation()
                o.load(obs)
                self.observations.append(o)

            # Don't like this. Do something better in the future
            for o in self.observations:
                if o.animal_id is not None:
                    o.animal = self.get_animal(o.animal_id)

            for att in GlobalFinPrintServer().attributes(id):
                self.attributes.append(att)

    def add_event(self, obs_id, evt_values):
        result = self._connection.add_event(self.id, obs_id, **evt_values)
        self._obs_from_json(result)
        return result['filename']

    def edit_event(self, evt, evt_values):
        result = self._connection.edit_event(self.id, evt.observation.id, evt.id, **evt_values)
        self._obs_from_json(result)

    def delete_event(self, evt):
        result = self._connection.delete_event(self.id, evt.observation.id, evt.id)
        self._obs_from_json(result)

    def add_observation(self, obs_values):
        result = self._connection.add_observation(self.id, **obs_values)
        self._obs_from_json(result)
        return result['filename']

    def edit_observation(self, obs):
        result = self._connection.edit_observation(self.id, obs)
        self._obs_from_json(result)

    def delete_observation(self, obs):
        result = self._connection.delete_observation(self.id, obs.id)
        self._obs_from_json(result)

    def _obs_from_json(self, json):
        self.observations = []
        for oj in json['observations']:
            o = Observation()
            o.load(oj)
            if o.animal_id:
                o.animal = self.get_animal(o.animal_id)
            self.observations.append(o)

    def get_animal(self, id):
        a = [animal for animal in self.animals if animal.id == id]
        if len(a):
            return a[0]
        return None

    def update_progress(self, progress):
        if self.assigned_to_current():
            GlobalFinPrintServer().update_progress(self.id, progress)

    def mark_as_done(self):
        GlobalFinPrintServer().mark_set_done(self.id)

    def assigned_to_current(self):
        return GlobalFinPrintServer().user_id == self.assigned_to['id']
