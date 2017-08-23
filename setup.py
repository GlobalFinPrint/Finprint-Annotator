#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import os
from os.path import isdir, islink
import shutil
import glob
from distutils.core import setup
from py2exe.distutils_buildexe import py2exe
import win32api, win32con
import config



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
                 version=config.__version_string__):
        self.lib_dir = lib_dir
        self.dist_dir = dist_dir
        if not self.dist_dir[-1] in "\\/":
            self.dist_dir += "\\"
        self.name = name
        self.version = version
        self.console_exe_files = [self.chop(p) for p in console_exe_files]
        self.windows_exe_files = [self.chop(p) for p in windows_exe_files]
        self.service_exe_files = [self.chop(p) for p in service_exe_files]
        self.lib_files = [p for p in lib_files]
        self.files_to_delete = []

    def chop(self, pathname):
        if pathname.startswith(self.dist_dir):
            return pathname[len(self.dist_dir):]
        return pathname

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

            print(r"[INI]", file=ofi)
            print(r'Filename: "{app}\config.ini"; Section: "VIDEOS"; Key: "alt_media_dir"; String: "{code:GetVideoDir|0}"',file=ofi)

            install_code = r"""
                                [Code]
                                var
                                  VideoDirPage: TInputDirWizardPage;

                                procedure InitializeWizard;
                                begin
                                  { Create the pages }
                                  VideoDirPage := CreateInputDirPage(wpSelectDir,
                                    'Select BRUV Video Destination Location',
                                    'Where should the Finprint-Annotator look for BRUV videos to view?',
                                    'Setup will set the default file path to BRUV videos to the following folder.'+
                                    'To continue, click Next. If you would like to select a different folder, click Browse.',
                                    False, '');
                                  VideoDirPage.Add('');

                                  { Set default values, using settings that were stored last time if possible }

                                  VideoDirPage.Values[0] := GetPreviousData('VideoDir', '');
                                end;

                                procedure RegisterPreviousData(PreviousDataKey: Integer);
                                begin
                                  { Store the settings so we can restore them next time }
                                  SetPreviousData(PreviousDataKey, 'VideoDir', VideoDirPage.Values[0]);
                                end;

                                function NextButtonClick(CurPageID: Integer): Boolean;
                                begin
                                  {
                                    Validate certain pages before allowing the user to proceed
                                    Weak assumption that there are 3 pages involved in installation
                                  }
                                  if not(CurPageID = VideoDirPage.ID) then
                                     if not(CurPageID = wpReady) then
                                    VideoDirPage.Values[0] := WizardDirValue + '\videos'

                                  Result := True;
                                end;

                                function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo, MemoTypeInfo,
                                                         MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
                                var
                                  S: String;
                                begin
                                  { Fill the 'Ready Memo' with the normal settings and the custom settings }
                                  S := '';
                                  S := S + MemoDirInfo + NewLine;
                                  S := S + Space + VideoDirPage.Values[0] + ' (video data files)' + NewLine;

                                  Result := S;
                                end;

                                function GetVideoDir(Param: String): String;
                                begin
                                  { Return the selected Video directory path }
                                  Result := VideoDirPage.Values[StrToInt(Param)];
                                end;
                                """
            print(install_code, file=ofi)

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


class BuildInstaller(py2exe):
    # This class first builds the exe file(s), then creates a Windows installer.
    # You need InnoSetup for it.

    def delete_helper(func, path, exc_info, test):
        print('Clearing attributes: %s' % path)
        win32api.SetFileAttributes(path, win32con.FILE_ATTRIBUTE_NORMAL)
        func(path)

    def pre_run(self):
        print('#################### pre_run ##################')
        if 'clean' in sys.argv:
            if os.path.exists('build'):
                print('Deleting build dir')
                shutil.rmtree('build', onerror=self.delete_helper)
            if os.path.exists(self.dist_dir):
                print('Deleting dist dir')
                shutil.rmtree(self.dist_dir, onerror=self.delete_helper)
        print('################## end pre_run ################')

    def run(self):
        self.pre_run()

        # let py2exe do it's work.
        py2exe.run(self)

        self.post_run()

        # create the Installer, using the files py2exe has created.
        script = InnoScript("Finprint-Annotator",
                            self.lib_dir,
                            self.dist_dir,
                            self.console_exe_files,
                            self.windows_exe_files,
                            self.service_exe_files,
                            self.lib_files,
                            config.__version_string__)
        print("*** creating the inno setup script***")
        script.create()
        print("*** compiling the inno setup script***")
        script.compile()

        self.post_installer()

    def post_run(self):
        print('#################### post_run ##################')

        # we don't need w9xpopen.exe
        temp_path = os.path.join(self.dist_dir, 'w9xpopen.exe')
        if os.path.exists(temp_path):
            os.remove(temp_path)

        # copy template ini files into dist dir, make sure they're editable
        shutil.copy('config.example.ini',
                    'dist/config.ini')
        win32api.SetFileAttributes('dist/config.ini',
                                    win32con.FILE_ATTRIBUTE_NORMAL)

        # include credentials file
        shutil.copy('credentials.csv', 'dist/credentials.csv')
        win32api.SetFileAttributes('dist/credentials.csv', win32con.FILE_ATTRIBUTE_NORMAL)

        shutil.copy('lib/mkl_intel_thread.dll',
                    'dist/mkl_intel_thread.dll')
        win32api.SetFileAttributes('dist/mkl_intel_thread.dll',
                                   win32con.FILE_ATTRIBUTE_NORMAL)

        shutil.copy('lib/opencv_ffmpeg310.dll',
                    'dist/opencv_ffmpeg310.dll')
        win32api.SetFileAttributes('dist/opencv_ffmpeg310.dll',
                                   win32con.FILE_ATTRIBUTE_NORMAL)

        shutil.copy('lib/numpy-atlas.dll',
                    'dist/numpy-atlas.dll')
        win32api.SetFileAttributes('dist/numpy-atlas.dll',
                                   win32con.FILE_ATTRIBUTE_NORMAL)

        shutil.copy('lib/libvlc.dll',
                    'dist/libvlc.dll')
        win32api.SetFileAttributes('dist/libvlc.dll',
                                    win32con.FILE_ATTRIBUTE_NORMAL)

        shutil.copy('lib/libvlccore.dll',
                    'dist/libvlccore.dll')
        win32api.SetFileAttributes('dist/libvlccore.dll',
                                   win32con.FILE_ATTRIBUTE_NORMAL)

        shutil.copytree('lib/plugins',
                     'dist/plugins')

        shutil.copy('requests/cacert.pem',
                    'dist/cacert.pem')
        win32api.SetFileAttributes('dist/cacert.pem',
                               win32con.FILE_ATTRIBUTE_NORMAL)

        self.lib_dir = "dist\\lib"
        self.lib_files = [] #self.getdatafiles()
        for path_tuple in (self.distribution.data_files):
            for path in path_tuple[1]:
                self.lib_files.append(path)

        # XXX hack for plugins to wind up at same level as libvlc
        lib_plugin_files = globr('lib\\plugins\\*')
        trimmed_plugins = trim_plugin_tree(lib_plugin_files)
        opencv_dlls = globr('dist\\opencv*')

        self.console_exe_files = ['finprint_annotator.exe', 'credentials.csv', 'cacert.pem', 'config.ini', 'lib/shared.zip', 'libvlc.dll', 'libvlccore.dll',
                                  'numpy-atlas.dll', 'mkl_intel_thread.dll', 'QTCore4.dll', 'QTGui4.dll', 'python34.dll'] + opencv_dlls +  trimmed_plugins
        self.windows_exe_files = []
        self.service_exe_files = []
        print('################## end post_run ################')

    def post_installer(self):
        print('#################### post_installer ##################')
        print('Clearing out Distribution dir')
        output = 'Distribution'
        #root = os.path.join(output, config.__version_string__ + '-dev')
        root = os.path.join(output, 'dev')
        binary = os.path.join(root, 'Binary')

        if os.path.exists(root):
            shutil.rmtree(root, onerror=self.delete_helper)
        print('Moving files into Distribution dir: %s' % root)
        os.makedirs(root)
        shutil.copytree('dist', binary)

        setup_files = glob.glob(binary + '/*_Setup.exe')
        for file in setup_files:
            shutil.move(file, root)
        print('################## end post_installer ################')

def globr(pattern):
    """ Recursive glob implementation """
    candidates = glob.glob(pattern)
    files = []
    for candidate in candidates:
        if isdir(candidate):
            files.extend(globr(os.path.join(candidate, "*")))
        elif islink(candidate):
            files.extend(globr(os.readlink(candidate)))
        else:
            files.append(candidate)
    return files

# XXX a hack to fit the plugins into the existing installer
def trim_plugin_tree(files):
    trimmed = []
    for file in files:
        if 'lib\\' in file:
            trimmed.append(file[4:])
        else:
            trimmed.append(file)
    return trimmed

def getdatafiles():
    data_files = []
    excluded_dirs = []
    excluded_file_extensions = ['.pyc', '.log']
    image_files = globr('images\\*')
    ffmpeg_executable = globr('ffmpeg_executable\\*')
    static_files = image_files
    static_files_dict = {}
    for f in static_files:
        ex = False
        for excluded in excluded_dirs:
            if f.startswith(excluded):
                ex = True
                continue
        for excluded in excluded_file_extensions:
            if f.endswith(excluded):
                ex = True
                continue
        if ex is True:
            continue
        dirname = os.path.dirname(f)
        if dirname not in static_files_dict:
            static_files_dict[dirname] = []
        static_files_dict[dirname].append(f)
    for key in static_files_dict:
        data_files.append((key, static_files_dict[key]))

    static_executable_files = ffmpeg_executable

    #adding for ffmpeg_exe
    for f in static_executable_files:
        ex = False
        for excluded in excluded_dirs:
            if f.startswith(excluded):
                ex = True
                continue
        for excluded in excluded_file_extensions:
            if f.endswith(excluded):
                ex = True
                continue
        if ex is True:
            continue
        dirname = os.path.dirname(f)
        if dirname not in static_files_dict:
            static_files_dict[dirname] = []
        static_files_dict[dirname].append(f)
    for key in static_files_dict:
        data_files.append((key, static_files_dict[key]))

    return data_files


app_target = Target(
        # We can extend or override the VersionInfo of the base class:
        # version = "1.0",
        # file_description = "File Description",
        # comments = "Some Comments",
        # internal_name = "spam",

        script="finprint_annotator.py",  # path of the main script

        # Icon resources:[(resource_id, path to .ico file), ...]
        icon_resources=[(1, r"images/shark-icon.ico")],

        other_resources=[
            (RT_MANIFEST, 1, (manifest_template % dict(prog="finprint_annotator", level="asInvoker")).encode("utf-8")),
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
        packages=['ctypes'],
        ##    excludes = "tof_specials Tkinter".split(),
        ##    ignores = "dotblas gnosis.xml.pickle.parsers._cexpat mx.DateTime".split(),
        ##    dll_excludes = "MSVCP90.dll mswsock.dll powrprof.dll".split(),
        optimize=0,
        compressed=False,  # uncompressed may or may not have a faster startup
        bundle_files=2,
        #dist_dir='.\\dist',
        includes=['sip'],
        excludes=[],
        dll_excludes=[]
)

setup(
        name='finprint-annotator',
        version=config.__version_string__,
        # packages=[''],
        url='',
        license='',
        author='Vulcan Inc',
        author_email='',
        description='',
        # console based executables
        console=[app_target],

        # for now, we are loading the plugis here
        data_files = getdatafiles(),
        # windows subsystem executables (no console)
        windows=[],

        # py2exe options
        zipfile="lib/shared.zip",
        options={"py2exe": py2exe_options},
        cmdclass={"py2exe": BuildInstaller}

)


