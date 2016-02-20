## modulesPage.py - show selinux mappings
## Copyright (C) 2006-2009 Red Hat, Inc.

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
import string
import gtk
import gtk.glade
import os
import subprocess
import gobject
import sys
import seobject
import selinux
from semanagePage import *
from subprocess import Popen, PIPE

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


class modulesPage(semanagePage):

    def __init__(self, xml):
        semanagePage.__init__(self, xml, "modules", _("Policy Module"))
        self.module_filter = xml.get_widget("modulesFilterEntry")
        self.module_filter.connect("focus_out_event", self.filter_changed)
        self.module_filter.connect("activate", self.filter_changed)
        self.audit_enabled = False

        self.store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.view.set_model(self.store)
        self.store.set_sort_column_id(0, gtk.SORT_ASCENDING)
        col = gtk.TreeViewColumn(_("Module Name"), gtk.CellRendererText(), text=0)
        col.set_sort_column_id(0)
        col.set_resizable(True)
        self.view.append_column(col)
        self.store.set_sort_column_id(0, gtk.SORT_ASCENDING)
        col = gtk.TreeViewColumn(_("Version"), gtk.CellRendererText(), text=1)
        self.enable_audit_button = xml.get_widget("enableAuditButton")
        self.enable_audit_button.connect("clicked", self.enable_audit)
        self.new_button = xml.get_widget("newModuleButton")
        self.new_button.connect("clicked", self.new_module)
        col.set_sort_column_id(1)
        col.set_resizable(True)
        self.view.append_column(col)
        self.store.set_sort_func(1, self.sort_int, "")
        status, self.policy_type = selinux.selinux_getpolicytype()

        self.load()

    def sort_int(self, treemodel, iter1, iter2, user_data):
        try:
            p1 = int(treemodel.get_value(iter1, 1))
            p2 = int(treemodel.get_value(iter1, 1))
            if p1 > p2:
                return 1
            if p1 == p2:
                return 0
            return -1
        except:
            return 0

    def load(self, filt=""):
        self.filter=filt
        self.store.clear()
        try:
            fd = Popen("semodule -l", shell=True, stdout=PIPE).stdout
            l = fd.readlines()
            fd.close()
            for i in l:
                module, ver, newline = i.split('\t')
                if not (self.match(module, filt) or self.match(ver, filt)):
                    continue
                it = self.store.append()
                self.store.set_value(it, 0, module.strip())
                self.store.set_value(it, 1, ver.strip())
        except:
            pass
        self.view.get_selection().select_path((0,))

    def new_module(self, args):
        try:
            Popen(["/usr/share/system-config-selinux/polgengui.py"])
        except ValueError as e:
            self.error(e.args[0])

    def delete(self):
        store, it = self.view.get_selection().get_selected()
        module = store.get_value(it, 0)
        self.wait()
        try:
            subprocess.check_output("semodule -r %s" % module,
                                    stderr=subprocess.STDOUT,
                                    shell=True)
            store.remove(it)
            self.view.get_selection().select_path ((0,))
        except subprocess.CalledProcessError as e:
            self.error(e.output)
        self.ready()

    def enable_audit(self, button):
        self.audit_enabled = not self.audit_enabled
        if self.audit_enabled:
            cmd = "semodule -DB"
            label = _("Disable Audit")
        else:
            cmd = "semodule -B"
            label = _("Enable Audit")
        self.wait()
        try:
            subprocess.check_output(cmd,
                                    stderr=subprocess.STDOUT,
                                    shell=True)
            button.set_label(label)
        except subprocess.CalledProcessError as e:
            self.error(e.output)
        self.ready()

    def disable_audit(self, button):
        self.wait()
        cmd = "semodule -B"
        try:
            subprocess.check_output(cmd,
                                    stderr=subprocess.STDOUT,
                                    shell=True)
        except subprocess.CalledProcessError as e:
            self.error(e.output)
        self.ready()

    def propertiesDialog(self):
        # Do nothing
        return

    def addDialog(self):
        dialog = gtk.FileChooserDialog(_("Load Policy Module"),
                                       None,
                                       gtk.FILE_CHOOSER_ACTION_OPEN,
                                       (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                        gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)

        filt = gtk.FileFilter()
        filt.set_name("Policy Files")
        filt.add_pattern("*.pp")
        dialog.add_filter(filt)

        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            self.add(dialog.get_filename())
        dialog.destroy()

    def add(self, file):
        self.wait()
        cmd = "semodule -i %s" % file
        try:
            subprocess.check_output(cmd,
                                    stderr=subprocess.STDOUT,
                                    shell=True)
            self.load()
        except subprocess.CalledProcessError as e:
            self.error(e.output)
        self.ready()

