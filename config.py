from configparser import ConfigParser

__version__ = (0, 1, 1, 0)
__version_string__ = '%s.%s.%s.%s' % __version__



class Config():
    CONFIG_FILENAME = './config.ini'
    def __init__(self):
        self._configdict = None

    def __contains__(self, item):
        return item in self._configdict

    def get(self, section=None, key=None):
        if self._configdict is None:
            try:
                self._configdict = ConfigParser()
                self._configdict.read(self.CONFIG_FILENAME)
            except:
                pass
        if section:
            return self._configdict[section][key]
        return self._configdict

    def __getitem__(self, key):
        return self._configdict[key]

    def __setitem__(self, key, value):
        self._configdict[key] = value

    def set(self, configdict):
        self._configdict = configdict

    def set_section(self, section_dict):
        self._configdict.update(section_dict)


global_config = Config()