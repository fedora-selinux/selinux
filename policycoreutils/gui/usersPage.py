## usersPage.py - show selinux mappings
## Copyright (C) 2006,2007,2008 Red Hat, Inc.

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
from gi.repository import Gtk
import Gtk.glade
from gi.repository import GObject
import subprocess
import seobject
from semanagePage import *;

##
## I18N
##
PROGNAME="policycoreutils"
import gettext
gettext.bindtextdomain(PROGNAME, "/usr/share/locale")
gettext.textdomain(PROGNAME)
try:
    gettext.install(PROGNAME, localedir="/usr/share/locale", unicode=1)
except IOError:
    import builtins
    builtins.__dict__['_'] = unicode

class usersPage(semanagePage):
    def __init__(self, xml):
        semanagePage.__init__(self, xml, "users", _("SELinux User"))

        self.store = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_STRING)
        self.view.set_model(self.store)
        self.store.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        col = Gtk.TreeViewColumn(_("SELinux\nUser"), Gtk.CellRendererText(), text = 0)
        col.set_sort_column_id(0)
        col.set_resizable(True)
        self.view.append_column(col)

        col = Gtk.TreeViewColumn(_("MLS/\nMCS Range"), Gtk.CellRendererText(), text = 1)
        col.set_resizable(True)
        self.view.append_column(col)

        col = Gtk.TreeViewColumn(_("SELinux Roles"), Gtk.CellRendererText(), text = 2)
        col.set_resizable(True)
        self.view.append_column(col)

        self.load()
        self.selinuxUserEntry = xml.get_widget("selinuxUserEntry")
        self.mlsRangeEntry = xml.get_widget("mlsRangeEntry")
        self.selinuxRolesEntry = xml.get_widget("selinuxRolesEntry")

    def load(self, filt = ""):
        self.filter=filt
        self.user = seobject.seluserRecords()
        udict = self.user.get_all()
        keys = list(udict.keys())
        keys.sort()
        self.store.clear()
        for k in keys:
            serange = seobject.translate(udict[k][2])
            if not (self.match(k, filt) or self.match(udict[k][0], filter) or self.match(serange, filt) or self.match(udict[k][3], filt)):
                continue

            it = self.store.append()
            self.store.set_value(it, 0, k)
            self.store.set_value(it, 1, serange)
            self.store.set_value(it, 2, udict[k][3])
        self.view.get_selection().select_path ((0,))

    def dialogInit(self):
        store, it = self.view.get_selection().get_selected()
        self.selinuxUserEntry.set_text(store.get_value(it, 0))
        self.selinuxUserEntry.set_sensitive(False)
        self.mlsRangeEntry.set_text(store.get_value(it, 1))
        self.selinuxRolesEntry.set_text(store.get_value(it, 2))

    def dialogClear(self):
        self.selinuxUserEntry.set_text("")
        self.selinuxUserEntry.set_sensitive(True)
        self.mlsRangeEntry.set_text("s0")
        self.selinuxRolesEntry.set_text("")

    def add(self):
        user = self.selinuxUserEntry.get_text()
        serange = self.mlsRangeEntry.get_text()
        roles = self.selinuxRolesEntry.get_text()

        self.wait()
        try:
            subprocess.check_output("semanage user -a -R '%s' -r %s %s" %  (roles, serange, user),
                                    stderr=subprocess.STDOUT,
                                    shell=True)
            self.ready()
            it = self.store.append()
            self.store.set_value(it, 0, user)
            self.store.set_value(it, 1, serange)
            self.store.set_value(it, 2, roles)
        except subprocess.CalledProcessError as e:
            self.error(e.output)
            self.ready()
            return False

    def modify(self):
        user = self.selinuxUserEntry.get_text()
        serange = self.mlsRangeEntry.get_text()
        roles = self.selinuxRolesEntry.get_text()

        self.wait()
        cmd = "semanage user -m -R '%s' -r %s %s" %  (roles, serange, user)
        try:
            subprocess.check_output(cmd,
                                    stderr=subprocess.STDOUT,
                                    shell=True)
            self.ready()
            self.load(self.filter)
        except subprocess.CalledProcessError as e:
            self.error(e.output)
            self.ready()
            return False
        return True

    def delete(self):
        store, it = self.view.get_selection().get_selected()
        try:
            user=store.get_value(it, 0)
            if user == "root" or user == "user_u":
                raise ValueError(_("SELinux user '%s' is required") % user)

            self.wait()
            cmd = "semanage user -d %s" %  user
            try:
                subprocess.check_output(cmd,
                                        stderr=subprocess.STDOUT,
                                        shell=True)
                self.ready()
                store.remove(it)
                self.view.get_selection().select_path ((0,))
            except subprocess.CalledProcessError as e:
                self.error(e.output)
                self.ready()
                return False
        except ValueError as e:
            self.error(e.args[0])
