import config


def get_vlc_params():
    plist = []
    cfg = config.global_config
    params = dict(cfg.items('vlc_params'))
    if params:

        for key, value in params.items():
            # we use the keyword 'True' or 'False' for any parameters
            # that don't have an associated value, like the param logFile.
            # If the value is 'True' we add the single argument parameter
            if value in ['True', 'False']:
                if value == 'True':
                    plist.append('--{0}'.format(key))
            else:
                plist.append('--{0}={1}'.format(key, value))

        return tuple(plist)

    return ()

def get_vlc_media_options():
    optlist = []
    cfg = config.global_config
    opts = dict(cfg.items('vlc_options'))
    if opts:

        for key, value in opts.items():
            optlist.append('{0}={1}'.format(key, value))
        return tuple(optlist)

    return ()