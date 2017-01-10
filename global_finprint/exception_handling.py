import requests
from logging import getLogger
import sys
import traceback
from config import global_config


class ExceptionHandling:
    def __init__(self):
        self.base_url = global_config.get('exception_handling_options', 'address')
        self.token = global_config.get('exception_handling_options', 'token')

    def log_error(self, severity='error', **kwargs):
        allowed_severities = ('info', 'debug', 'warning', 'error')
        if severity not in allowed_severities:
            getLogger('finprint').warning('Severity must one one of {}'.format(allowed_severities))
            return None
        if self.token == '~TOKEN GOES HERE~':
            getLogger('finprint').warning('Token must be specified in config.ini')
            return None
        data = {
            'token': self.token,
            'severity': severity,
            'api_server': global_config.get('GLOBAL_FINPRINT_SERVER', 'address'),
            'error': traceback.format_exception(*sys.exc_info())
        }
        data.update(kwargs)
        return requests.post('{}/new'.format(self.base_url), data)

    def heartbeat(self):
        return requests.get('{}/heartbeat'.format(self.base_url))
