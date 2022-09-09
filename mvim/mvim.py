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
from shutil import rmtree
from pathlib import Path

import enum


class Answer(enum.Enum):

    YES = "y"
    NO = "n"
    QUIT = "q"
    ALWAYS = "a"
    NEVER = "d"
    HELP = "?"

    def basic(self):
        if self == Answer.ALWAYS:
            return Answer.YES
        elif self == Answer.NEVER:
            return Answer.NO
        else:
            return self

    def storable(self):
        return self in (
            Answer.ALWAYS,
            Answer.NEVER,
        )


class UI:
    def __init__(self):
        self.answers = {}

    def ask(self, question, key):
        try:
            # Search for an already known answer
            return self.answers[key]
        except KeyError:
            return self._do_ask(question, key)

    def _do_ask(self, question, key):
        # Answer not known, ask for it
        try:
            ans = input(question + " [y,n,q,a,d,?] ").lower()
            ans = Answer(ans[0])
            if ans == Answer.QUIT:
                raise KeyboardInterrupt()
            if ans == Answer.HELP:
                raise ValueError()
            if ans.storable():
                ans = self.answers[key] = ans.basic() == Answer.YES
            else:
                ans = ans == Answer.YES
            return ans
        except (ValueError, IndexError):
            print("y: yes, n: no, a: always, d: never, q: quit, ?: help")
            return self._do_ask(question, key)


class MVim:
    def __init__(
        self,
        files,
        *,
        all_files=False,
        follow_symlinks=False,
        force=False,
        recursive=False,
        windows=False,
        diff=False,
        meld=False,
        cmd=None,
    ):

        self.all_files = all_files
        self.follow_symlinks = follow_symlinks
        self.force = force
        self.recursive = recursive
        self.windows = windows
        self.diff = diff
        self.cmd = cmd

        self.ui = UI()

        if meld:
            self.cmd = "meld"
            self.diff = True

        self.oldnames = []
        self.added_dir = []
        self.added_files = []

        for f in files:
            self.add(f)

        # Create a temporary file with new filenames.
        self.new_names_file = NamedTemporaryFile(prefix="mvim.newnames.", mode="w+t")
        self.save_names_to_tmp(self.oldnames, self.new_names_file)

        # Create a temporary file with old filenames if necessary.
        if self.windows or self.diff:
            self.old_names_file = NamedTemporaryFile(prefix="mvim.oldnames.", mode="w+t")
            self.save_names_to_tmp(self.oldnames, self.old_names_file)

        self.edit()

    def save_names_to_tmp(self, names, tmpfile):
        for name in names:
            tmpfile.write(name.as_posix() + "\n")
        tmpfile.file.flush()

    def add(self, path):
        if path.is_symlink() and self.follow_symlinks:
            path = path.resolve().relative_to(Path.cwd())

        if path.is_dir():
            self.oldnames.extend(
                sorted(
                    [
                        p
                        for p in path.iterdir()
                        if self.all_files or not p.as_posix().startswith(".")
                    ]
                )
            )
        elif path.is_file() or path.is_symlink():
            self.oldnames.append(path)
        else:
            print(f"Warning: ignoring '{path}': no such file or directory", file=sys.stderr)

    def open_vim(self):
        if self.cmd:
            if self.diff or self.windows:
                subprocess.call(
                    [
                        self.cmd,
                        self.old_names_file.name,
                        self.new_names_file.name,
                    ]
                )
            else:
                subprocess.call(
                    [
                        self.cmd,
                        self.new_names_file.name,
                    ]
                )
        elif self.diff:
            subprocess.call(
                [
                    "vim",
                    # Open the list of old file names (RO).
                    "-c",
                    "view " + self.old_names_file.name,
                    "-c",
                    "diffthis",
                    # Open the list of new file names in a new window (RW).
                    "-c",
                    "set splitright",
                    "-c",
                    "vsp",
                    "-c",
                    "edit " + self.new_names_file.name,
                    "-c",
                    "diffthis",
                    # Open folds, Vim automatically folds everything since there is no difference.
                    "-c",
                    "foldopen",
                ]
            )
        elif self.windows:
            subprocess.call(
                [
                    "vim",
                    # Open the list of old file names (RO).
                    "-c",
                    "view " + self.old_names_file.name,
                    # Open the list of new file names in a new window (RW).
                    "-c",
                    "set splitright",
                    "-c",
                    "vsp",
                    "-c",
                    "edit " + self.new_names_file.name,
                ]
            )
        else:
            subprocess.call(["vim", self.new_names_file.name])

    def edit(self):
        while True:
            self.open_vim()
            self.new_names_file.file.seek(os.SEEK_SET)
            newnames = [Path(line.strip()) for line in self.new_names_file.file.readlines()]
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

        for newpath, oldpath in zip(newnames, self.oldnames):
            if newpath == Path("."):
                self.delete(oldpath)
            elif newpath != oldpath:
                self.rename(oldpath, newpath)
            # else newname == oldname: pass

    def delete(self, path):
        if self.force or self.ui.ask(f"Delete '{path}' ?", key="del"):
            self._do_delete(path)
        else:
            print(f"Skipping '{path}' ...")

    def _do_delete(self, path):
        try:
            if self.recursive and path.is_dir() and not path.is_symlink():
                rmtree(path)
            else:
                path.unlink()
        except OSError as e:
            print(f"Error: cannot remove '{path}':", e.strerror, file=sys.stderr)

    def rename(self, oldpath, newpath):
        try:
            newpath.parent.mkdir(exist_ok=True)
            if not newpath.exists() or self.ui.ask(f"Overwrite '{newpath}'?", key="over"):
                oldpath.rename(newpath)
                print(f"'{oldpath}' -> '{newpath}'", file=sys.stderr)
            else:
                print(f"Skipping '{oldpath}' ...")

        except OSError as e:
            print(f"Error: cannot move '{oldpath}' to '{newpath}':", e.strerror, file=sys.stderr)


def query_yes_no(question, default=True):
    """Ask a yes/no question via input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be True (the default), False or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    if default is None:
        prompt = " [y/n] "
    elif default:
        prompt = " [Y/n] "
    else:
        prompt = " [y/N] "

    while True:
        print(question + prompt, end="")
        choice = input().lower()
        if default is not None and choice == "":
            return default
        elif "yes".startswith(choice):
            return True
        elif "no".startswith(choice):
            return False
        else:
            print("Please respond with 'yes' or 'no' (or 'y' or 'n').")
