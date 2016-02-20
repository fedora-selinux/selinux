## loginsPage.py - show selinux mappings
## Copyright (C) 2006 Red Hat, Inc.

## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

## Author: Dan Walsh
import gtk
import gtk.glade
import gobject
import subprocess
import seobject
from semanagePage import *

##
## I18N
##
PROGNAME = "policycoreutils"
import gettext
gettext.bindtextdomain(PROGNAME, "/usr/share/locale")
gettext.textdomain(PROGNAME)
try:
    gettext.install(PROGNAME,
                    localedir="/usr/share/locale",
                    unicode=False,
                    codeset='utf-8')
except IOError:
    import builtins
    builtins.__dict__['_'] = str


class loginsPage(semanagePage):

    def __init__(self, xml):
        self.firstTime = False
        semanagePage.__init__(self, xml, "logins", _("User Mapping"))
        self.store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.view.set_model(self.store)
        self.store.set_sort_column_id(0, gtk.SORT_ASCENDING)
        col = gtk.TreeViewColumn(_("Login\nName"), gtk.CellRendererText(), text=0)
        col.set_sort_column_id(0)
        col.set_resizable(True)
        self.view.append_column(col)
        col = gtk.TreeViewColumn(_("SELinux\nUser"), gtk.CellRendererText(), text=1)
        col.set_resizable(True)
        self.view.append_column(col)
        col = gtk.TreeViewColumn(_("MLS/\nMCS Range"), gtk.CellRendererText(), text=2)
        col.set_resizable(True)
        self.view.append_column(col)
        self.load()
        self.loginsNameEntry = xml.get_widget("loginsNameEntry")
        self.loginsSelinuxUserCombo = xml.get_widget("loginsSelinuxUserCombo")
        self.loginsMLSEntry = xml.get_widget("loginsMLSEntry")

    def load(self, filter=""):
        self.filter = filter
        self.login = seobject.loginRecords()
        dict = self.login.get_all(0)
        keys = list(dict.keys())
        keys.sort()
        self.store.clear()
        for k in keys:
            range = seobject.translate(dict[k][1])
            if not (self.match(k, filter) or self.match(dict[k][0], filter) or self.match(range, filter)):
                continue
            it = self.store.append()
            self.store.set_value(it, 0, k)
            self.store.set_value(it, 1, dict[k][0])
            self.store.set_value(it, 2, range)
        self.view.get_selection().select_path ((0,))

    def __dialogSetup(self):
        if self.firstTime:
            return
        self.firstTime = True
        liststore = gtk.ListStore(gobject.TYPE_STRING)
        self.loginsSelinuxUserCombo.set_model(liststore)
        cell = gtk.CellRendererText()
        self.loginsSelinuxUserCombo.pack_start(cell, True)
        self.loginsSelinuxUserCombo.add_attribute(cell, 'text', 0)

        selusers = seobject.seluserRecords().get_all(0)
        keys = list(selusers.keys())
        keys.sort()
        for k in keys:
            if k != "system_u":
                self.loginsSelinuxUserCombo.append_text(k)

        it = liststore.get_iter_first()
        while liststore.get_value(it,0) != "user_u":
            it = liststore.iter_next(it)
        self.loginsSelinuxUserCombo.set_active_iter(it)

    def dialogInit(self):
        self.__dialogSetup()
        store, it = self.view.get_selection().get_selected()
        self.loginsNameEntry.set_text(store.get_value(it, 0))
        self.loginsNameEntry.set_sensitive(False)

        self.loginsMLSEntry.set_text(store.get_value(it, 2))
        seuser = store.get_value(it, 1)
        liststore = self.loginsSelinuxUserCombo.get_model()
        it = liststore.get_iter_first()
        while it != None and liststore.get_value(it,0) != seuser:
            it = liststore.iter_next(it)
        if it != None:
            self.loginsSelinuxUserCombo.set_active_iter(it)

    def dialogClear(self):
        self.__dialogSetup()
        self.loginsNameEntry.set_text("")
        self.loginsNameEntry.set_sensitive(True)
        self.loginsMLSEntry.set_text("s0")

    def delete(self):
        store, it = self.view.get_selection().get_selected()
        try:
            login=store.get_value(it, 0)
            if login == "root" or login == "__default__":
                raise ValueError(_("Login '%s' is required") % login)

            self.wait()
            try:
                subprocess.check_output("semanage login -d %s" % login,
                                        stderr=subprocess.STDOUT,
                                        shell=True)
                self.ready()
                store.remove(it)
                self.view.get_selection().select_path ((0,))
            except subprocess.CalledProcessError as e:
                self.ready()
                self.error(e.output)
                return False
        except ValueError as e:
            self.error(e.args[0])

    def add(self):
        target = self.loginsNameEntry.get_text().strip()
        serange = self.loginsMLSEntry.get_text().strip()
        if serange == "":
            serange="s0"
        list_model=self.loginsSelinuxUserCombo.get_model()
        it = self.loginsSelinuxUserCombo.get_active_iter()
        seuser = list_model.get_value(it,0)
        self.wait()
        try:
            subprocess.check_output("semanage login -a -s %s -r %s %s" % (seuser, serange, target),
                                    stderr=subprocess.STDOUT,
                                    shell=True)
            self.ready()
            it = self.store.append()
            self.store.set_value(it, 0, target)
            self.store.set_value(it, 1, seuser)
            self.store.set_value(it, 2, seobject.translate(serange))
        except subprocess.CalledProcessError as e:
            self.error(e.output)
            self.ready()
            return False

    def modify(self):
        target = self.loginsNameEntry.get_text().strip()
        serange = self.loginsMLSEntry.get_text().strip()
        if serange == "":
            serange = "s0"
        list_model = self.loginsSelinuxUserCombo.get_model()
        it = self.loginsSelinuxUserCombo.get_active_iter()
        seuser=list_model.get_value(it,0)
        self.wait()
        try:
            subprocess.check_output("semanage login -m -s %s -r %s %s" % (seuser, serange, target),
                                    stderr=subprocess.STDOUT,
                                    shell=True)
            self.ready()
            store, it = self.view.get_selection().get_selected()
            self.store.set_value(it, 0, target)
            self.store.set_value(it, 1, seuser)
            self.store.set_value(it, 2, seobject.translate(serange))
        except subprocess.CalledProcessError as e:
            self.error(e.output)
            self.ready()
            return False
