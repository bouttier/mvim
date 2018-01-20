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

    def __init__(self, files, *, all_files=False, follow_symlinks=False,
                 force=False, recursive=False, windows=False, diff=False,
                 meld=False, cmd=None):

        self.all_files = all_files
        self.follow_symlinks = follow_symlinks
        self.force = force
        self.recursive = recursive
        self.windows = windows
        self.diff = diff
        self.cmd = cmd

        if meld:
            self.cmd = 'meld'
            self.diff = True

        self.oldnames = []
        self.added_dir = []
        self.added_files = []

        for file in files:
            self.add(file)

        # Create a temporary file with new filenames.
        self.new_names_file = NamedTemporaryFile(prefix='mvim.newnames.')
        self.save_names_to_tmp(self.oldnames, self.new_names_file)

        # Create a temporary file with old filenames if necessary.
        if self.windows or self.diff:
            self.old_names_file = NamedTemporaryFile(prefix='mvim.oldnames.')
            self.save_names_to_tmp(self.oldnames, self.old_names_file)

        self.edit()


    def save_names_to_tmp(self, names, tmpfile):
        for name in names:
            tmpfile.write((name + '\n').encode('utf8'))
        tmpfile.file.flush()


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
            print(f"Warning: ignoring '{file}': no such file or directory",
                  file=sys.stderr)


    def open_vim(self):
        if self.cmd:
            if self.diff or self.windows:
                subprocess.call([
                    self.cmd,
                    self.old_names_file.name,
                    self.new_names_file.name,
                ])
            else:
                subprocess.call([
                    self.cmd,
                    self.new_names_file.name,
                ])
        elif self.diff:
            subprocess.call([
                'vim',
                # Open the list of old file names (RO).
                '-c', 'view ' + self.old_names_file.name,
                '-c', 'diffthis',
                # Open the list of new file names in a new window (RW).
                '-c', 'set splitright',
                '-c', 'vsp',
                '-c', 'edit ' + self.new_names_file.name,
                '-c', 'diffthis',
                # Open folds, Vim automatically folds everything since there is no difference.
                '-c', 'foldopen'
            ])
        elif self.windows:
            subprocess.call([
                'vim',
                # Open the list of old file names (RO).
                '-c', 'view ' + self.old_names_file.name,
                # Open the list of new file names in a new window (RW).
                '-c', 'set splitright',
                '-c', 'vsp',
                '-c', 'edit ' + self.new_names_file.name
            ])
        else:
            subprocess.call(['vim', self.new_names_file.name])


    def edit(self):
        while True:
            self.open_vim()
            self.new_names_file.file.seek(os.SEEK_SET)
            newnames = []
            while True:
                line = self.new_names_file.file.readline()
                if line == b'':
                    break
                newnames.append(line.strip().decode('utf8'))
            if len(newnames) != len(self.oldnames):
                i = len(newnames) - len(self.oldnames)
                if i > 0:
                    verb = "added"
                else:
                    verb = "removed"
                print(f"Error: you {verb} {abs(i)} line{'' if abs(i) == 1 else 's'}")
                if not query_yes_no("Would you like edit file list again ?"):
                    return
            else:
                break

        for i in range(0, len(newnames)):
            if newnames[i] == "":
                if self.force or query_yes_no(f"Are you sure to delete '{self.oldname[i]}' ?", "no"):
                    if self.recursive and os.path.isdir(self.oldnames[i]) \
                            and not os.path.islink(self.oldnames[i]):
                        rmtree(self.oldnames[i])
                    else:
                        try:
                            os.remove(self.oldnames[i])
                        except Exception as e:
                            print(f"Error: can not delete '{self.oldname[i]}':", e.strerror)
                else:
                    print(f"Skipping '{self.oldnames[i]}' ...")
            elif not newnames[i] == self.oldnames[i]:
                print(f"Rename '{self.oldnames[i]}' to '{newnames[i]}' ...")
                if os.path.dirname(newnames[i]):
                    os.makedirs(os.path.dirname(newnames[i]), exist_ok=True)
                if not os.path.lexists(newnames[i]) or query_yes_no('Destination exists, override?', 'no'):
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
        raise ValueError(f"invalid default answer: '{default}'")

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
