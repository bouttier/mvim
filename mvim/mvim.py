"""
   Copyright 2014 Elie Bouttier

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and 
   limitations under the License.
"""

import os
import sys
from tempfile import NamedTemporaryFile
import subprocess
from argparse import ArgumentParser
from shutil import rmtree


class MVim:

    def __init__(self, files, **kwargs):

        self.all_files = False # do not ignore entires startinng with .
        self.follow_symlinks = False
        self.force = False # force remove without asking
        self.recursive = False # recursively remove directory

        for arg in kwargs:
            if arg == 'all_files':
                self.all_files = kwargs[arg]
            elif arg == 'follow_symlinks':
                self.follow_symlinks = kwargs[arg]
            elif arg == 'force':
                self.force = kwargs[arg]
            elif arg == 'recursive':
                self.recursive = kwargs[arg]
            else:
                print("Warning: ignoring invalid option '%s'" %arg,
                        file=sys.stdout)

        self.oldnames = []
        self.added_dir = []
        self.added_files = []

        for file in files:
            self.add(file)

        self.tmpfile = NamedTemporaryFile(prefix='mvim.')
        for name in self.oldnames:
            self.tmpfile.write(("%s\n" %name).encode('utf8'))
        self.tmpfile.file.flush()

        self.edit()

    def add(self, file):
    
        if os.path.lexists(file):

            if os.path.isdir(file):
                if not self.follow_symlinks and os.path.islink(file):
                    self.oldnames += [ file ]
                    return
                added = False
                for added_dir in self.added_dir:
                    try:
                        if os.path.samefile(added_dir, file):
                            added = True
                            break
                    except OSError:
                        pass
                if not added:
                    self.added_dir.append(file)
                    listdir = os.listdir(file)
                    listdir.sort()
                    if not self.all_files:
                        listdir = [ x for x in listdir if x[0] != '.' ]
                    if file != '.':
                        self.oldnames += list(map(lambda x:
                            os.path.join(file, x), listdir))
                    else:
                        self.oldnames += listdir
            elif os.path.isfile(file):
                added = False
                for added_file in self.added_files:
                    try:
                        if added_file == file:
                            added = True
                            break
                    except OSError:
                        pass
                if not added:
                    self.added_files.append(file)
                    self.oldnames += [ file ]

        else:
            print("Warning: ignoring '%s': no such file or directory" %file,
                    file=sys.stderr)

    def edit(self):
        while True:
            subprocess.call(['vim', self.tmpfile.name])
            self.tmpfile.file.seek(os.SEEK_SET)
            newnames = []
            while True:
                line = self.tmpfile.file.readline()
                if line == b'':
                    break
                newnames.append(line.strip().decode('utf8'))
            if len(newnames) != len(self.oldnames):
                i = len(newnames) - len(self.oldnames)
                if i > 0:
                    verb = "added"
                else:
                    verb = "removed"
                plural = ""
                if abs(i) != 1:
                    plural = "s"
                print("Error: you %s %d line%s" %(verb, abs(i), plural))
                if not query_yes_no("Would you like edit file list again ?"):
                    return
            else:
                break

        for i in range(0, len(newnames)):
            if newnames[i] == "":
                if self.force or query_yes_no("Are you sure to delete '%s' ?"
                        %self.oldnames[i], "no"):
                    if self.recursive and os.path.isdir(self.oldnames[i]) \
                            and not os.path.islink(self.oldnames[i]):
                        rmtree(self.oldnames[i])
                    else:
                        try:
                            os.remove(self.oldnames[i])
                        except Exception as e:
                            print("Error: can not delete '%s':"
                                    %self.oldnames[i], e.strerror)
                else:
                    print("Skipping '%s' ..." %self.oldnames[i])
            elif not newnames[i] == self.oldnames[i]:
                print("Rename '%s' to '%s' ..."
                        %(self.oldnames[i], newnames[i]))
                os.rename(self.oldnames[i], newnames[i])

def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {"yes":True,   "y":True,  "ye":True,
             "no":False,     "n":False}
    if default == None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        print(question + prompt, end='')
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            print("Please respond with 'yes' or 'no' "\
                             "(or 'y' or 'n').")
