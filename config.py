from configparser import ConfigParser


class Config():
    def __init__(self):
        self.parser = ConfigParser()
        self.parser.read('./config.ini')


global_config = Config()