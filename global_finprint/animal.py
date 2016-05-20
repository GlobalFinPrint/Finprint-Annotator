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
        if self.id is not None:
            return "{0} ({1} {2})".format(self.common_name, self.genus, self.species)
        else:
            return ''
