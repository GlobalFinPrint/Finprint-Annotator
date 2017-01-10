from math import floor


def convert_position(pos):
    s, m = divmod(floor(pos), 1000)
    h, s = divmod(s, 60)
    pos = "{0:02}:{1:02}:{2:03}".format(h, s, m)
    return pos


