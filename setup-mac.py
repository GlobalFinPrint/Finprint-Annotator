"""
This is a setup.py script generated by py2applet

Usage:
    python setup-mac.py py2app
"""

# monkeypatch py2app for symlink fix
import os
import py2app.build_app
def copy_dylib(self, src):
    if os.path.islink(src):
        dest = os.path.join(self.dest, os.path.basename(os.path.realpath(src)))
        link_dest = os.path.join(self.dest, os.path.basename(src))
        if os.path.basename(link_dest) != os.path.basename(dest) and not os.path.isfile(link_dest):
            os.symlink(os.path.basename(dest), link_dest)
    else:
        dest = os.path.join(self.dest, os.path.basename(src))
    return self.appbuilder.copy_dylib(src, dest)
py2app.build_app.PythonStandalone.copy_dylib = copy_dylib


from setuptools import setup

APP = ['finprint_annotator.py']

DATA_FILES = [
    'config.ini',
    'qt.conf',
    'annotation_view.py',
    'config.py',
    'global_finprint.py',
    'video_player.py',
]

OPTIONS = {
    'iconfile': 'images/shark-icon.icns',
    'resources': 'images',
    'includes': 'sip',
    'packages': 'PyQt4',
    'frameworks': '/usr/local/Cellar/hdf5/1.8.16_1/lib/libhdf5.10.dylib',
}

setup(
    name='FinPrint Annotator',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
