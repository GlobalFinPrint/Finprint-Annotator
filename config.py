from configparser import ConfigParser

__version__ = (1, 0, 0, 0)
__version_string__ = '%s.%s.%s.%s' % __version__


class Config():
    CONFIG_FILENAME = './config.ini'

    def __init__(self):
        self._configdict = None

    def __contains__(self, item):
        return item in self._configdict

    def save(self):
        with open(self.CONFIG_FILENAME, 'w') as file:
            self._configdict.write(file)

    def get(self, section=None, key=None):
        if self._configdict is None:
            try:
                self._configdict = ConfigParser()
                self._configdict.read(self.CONFIG_FILENAME)
            except:
                pass
        if section:
            if key in self._configdict[section]:
                return self._configdict[section][key]
            else:
                return None
        return self._configdict

    def __getitem__(self, key):
        return self._configdict[key]

    def __setitem__(self, key, value):
        self._configdict[key] = value

    def set(self, configdict):
        self._configdict = configdict
        self.save()

    def set_section(self, section_dict):
        self._configdict.update(section_dict)
        self.save()

    def set_item(self, section, key, value):
        try:
            self._configdict[section][key] = value
            self.save()
        except KeyError:
            pass


global_config = Config()
