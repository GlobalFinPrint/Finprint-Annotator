from math import floor


def convert_position(pos):
    print(pos)
    s, m = divmod(floor(pos), 1000)
    h, s = divmod(s, 60)
    return "{0:02}:{1:02}:{2:03}".format(h, s, m)

def millis_to_time(ms):
    x = ms / 1000
    s = x % 60
    x /= 60
    m = x % 60
    x /= 60
    h = x % 24
    return "{0:02}:{1:02}:{2:03}".format(h, s, m)

