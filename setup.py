#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Created by: python.exe -m py2exe main_window.py -W mysetup.py

import sys
import os
import os.path
import shutil
import glob
from distutils.core import setup
import py2exe

INNOSETUP_COMPILER = r'C:\InnoSetup\ISCC.exe'


############################################################
class InnoScript:
    def __init__(self,
                 name,
                 lib_dir,
                 dist_dir,
                 console_exe_files=[],
                 windows_exe_files=[],
                 service_exe_files=[],
                 lib_files=[],
                 version="1.0"):
        self.lib_dir = lib_dir
        self.dist_dir = dist_dir
        if not self.dist_dir[-1] in "\\/":
            self.dist_dir += "\\"
        self.name = name
        self.version = version
        self.console_exe_files = [self.chop(p) for p in console_exe_files]
        self.windows_exe_files = [self.chop(p) for p in windows_exe_files]
        self.service_exe_files = [self.chop(p) for p in service_exe_files]
        self.lib_files = [self.chop(p) for p in lib_files]
        self.files_to_delete = []

    def chop(self, pathname):
        assert pathname.startswith(self.dist_dir)
        return pathname[len(self.dist_dir):]

    def create(self, pathname=None):
        if not pathname:
            pathname = os.path.join(self.dist_dir, self.name) + '.iss'
        print("InnoSetup script: %s" % pathname)
        self.pathname = pathname
        with open(pathname, "w") as ofi:
            print("; WARNING: This script has been created by py2exe. Changes to this script", file=ofi)
            print("; will be overwritten the next time py2exe is run!\n", file=ofi)
            print(r"[Setup]", file=ofi)
            print(r"AppName=%s" % self.name, file=ofi)
            print(r"AppVersion=%s" % (self.version), file=ofi)
            print(r"AppVerName=%s %s" % (self.name, self.version), file=ofi)
            print(r"AppPublisher=Vulcan Inc.", file=ofi)
            print(r"DefaultDirName=C:\Vulcan\%s" % self.name, file=ofi)
            print(r"DefaultGroupName=%s" % self.name, file=ofi)
            print(r"Compression=zip", file=ofi)
            print(r"OutputDir=%s" % self.dist_dir, file=ofi)
            print(r"OutputBaseFilename=%s_%s_Setup" % (self.name,self.version), file=ofi)
            print("", file=ofi)

            print(r"[Files]", file=ofi)
            for path in (self.console_exe_files + self.lib_files + self.service_exe_files + self.windows_exe_files):
                flags = 'ignoreversion'
                print(r'Source: "%s"; DestDir: "{app}\%s"; Flags: %s' % (path, os.path.dirname(path), flags), file=ofi)

            print(r"[InstallDelete]", file=ofi)
            for path in self.files_to_delete:
                print(r'Type: filesandordirs; Name: "{app}\%s"' % path, file=ofi)

            print("",file=ofi)

    def compile(self):
        cmd = "%s %s" % (INNOSETUP_COMPILER, self.pathname)
        print("Running InnoSetup: %s" % cmd)
        error_level = os.system(cmd)
        print("InnoSetup returned error level: %s" % error_level)


excludes = ["Tkinter"]


class Target(object):
    '''Target is the baseclass for all executables that are created.
    It defines properties that are shared by all of them.
    '''

    def __init__(self, **kw):
        self.__dict__.update(kw)

        # the VersionInfo resource, uncomment and fill in those items
        # that make sense:

        # The 'version' attribute MUST be defined, otherwise no versioninfo will be built:
        # self.version = "1.0"

        # self.company_name = "Company Name"
        # self.copyright = "Copyright Company Name © 2013"
        # self.legal_copyright = "Copyright Company Name © 2013"
        # self.legal_trademark = ""
        # self.product_version = "1.0.0.0"
        # self.product_name = "Product Name"

        # self.private_build = "foo"
        # self.special_build = "bar"

    def copy(self):
        return Target(**self.__dict__)

    def __setitem__(self, name, value):
        self.__dict__[name] = value


RT_BITMAP = 2
RT_MANIFEST = 24

# A manifest which specifies the executionlevel
# and windows common-controls library version 6

manifest_template = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity
    version="5.0.0.0"
    processorArchitecture="*"
    name="%(prog)s"
    type="win32"
  />
  <description>%(prog)s</description>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel
            level="%(level)s"
            uiAccess="false">
        </requestedExecutionLevel>
      </requestedPrivileges>
    </security>
  </trustInfo>
  <dependency>
    <dependentAssembly>
        <assemblyIdentity
            type="win32"
            name="Microsoft.Windows.Common-Controls"
            version="6.0.0.0"
            processorArchitecture="*"
            publicKeyToken="6595b64144ccf1df"
            language="*"
        />
    </dependentAssembly>
  </dependency>
</assembly>
'''

main_window = Target(
        # We can extend or override the VersionInfo of the base class:
        # version = "1.0",
        # file_description = "File Description",
        # comments = "Some Comments",
        # internal_name = "spam",

        script="main_window.py",  # path of the main script

        # Allows to specify the basename of the executable, if different from 'main_window'
        # dest_base = "main_window",

        # Icon resources:[(resource_id, path to .ico file), ...]
        # icon_resources=[(1, r"main_window.ico")]

        other_resources=[
            (RT_MANIFEST, 1, (manifest_template % dict(prog="main_window", level="asInvoker")).encode("utf-8")),
            # for bitmap resources, the first 14 bytes must be skipped when reading the file:
            #                    (RT_BITMAP, 1, open("bitmap.bmp", "rb").read()[14:]),
            ]
)

# ``zipfile`` and ``bundle_files`` options explained:
# ===================================================
#
# zipfile is the Python runtime library for your exe/dll-files; it
# contains in a ziparchive the modules needed as compiled bytecode.
#
# If 'zipfile=None' is used, the runtime library is appended to the
# exe/dll-files (which will then grow quite large), otherwise the
# zipfile option should be set to a pathname relative to the exe/dll
# files, and a library-file shared by all executables will be created.
#
# The py2exe runtime *can* use extension module by directly importing
# the from a zip-archive - without the need to unpack them to the file
# system.  The bundle_files option specifies where the extension modules,
# the python dll itself, and other needed dlls are put.
#
# bundle_files == 3:
#     Extension modules, the Python dll and other needed dlls are
#     copied into the directory where the zipfile or the exe/dll files
#     are created, and loaded in the normal way.
#
# bundle_files == 2:
#     Extension modules are put into the library ziparchive and loaded
#     from it directly.
#     The Python dll and any other needed dlls are copied into the
#     directory where the zipfile or the exe/dll files are created,
#     and loaded in the normal way.
#
# bundle_files == 1:
#     Extension modules and the Python dll are put into the zipfile or
#     the exe/dll files, and everything is loaded without unpacking to
#     the file system.  This does not work for some dlls, so use with
#     caution.
#
# bundle_files == 0:
#     Extension modules, the Python dll, and other needed dlls are put
#     into the zipfile or the exe/dll files, and everything is loaded
#     without unpacking to the file system.  This does not work for
#     some dlls, so use with caution.


py2exe_options = dict(
        packages=[],
        ##    excludes = "tof_specials Tkinter".split(),
        ##    ignores = "dotblas gnosis.xml.pickle.parsers._cexpat mx.DateTime".split(),
        ##    dll_excludes = "MSVCP90.dll mswsock.dll powrprof.dll".split(),
        optimize=0,
        compressed=False,  # uncompressed may or may not have a faster startup
        bundle_files=0,
        dist_dir='dist',
        includes=["sip"]
)

setup(
        name='finprint-annotator',
        version='1.0.0',
        packages=[''],
        url='',
        license='',
        author='Vulcan Inc',
        author_email='',
        description='',
        # console based executables
        console=[main_window],

        # windows subsystem executables (no console)
        windows=[],

        # py2exe options
        zipfile="lib/shared.zip",
        options={"py2exe": py2exe_options},

)

# Some options can be overridden by command line options...

setup(name="name",
      # console based executables
      console=[main_window],

      # windows subsystem executables (no console)
      windows=[],

      # py2exe options
      zipfile=None,
      options={"py2exe": py2exe_options},
      )
