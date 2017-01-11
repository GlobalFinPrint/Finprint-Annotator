import config


def get_vlc_params():
    plist = []
    cfg = config.global_config

    params = dict(cfg.items('vlc_params'))
    for key, value in params.items:
        if value is not 'None':
            plist.append('--{0}={1}'.format(key, value))
        else:
            plist.append('--{0}'.format(key))

    return tuple(plist)

def get_vlc_options():
    cfg = config.global_config

    opts = dict(cfg.items('vlc_options'))
    if opts:
        return opts.items()
    return []