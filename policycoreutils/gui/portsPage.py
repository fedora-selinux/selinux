## portsPage.py - show selinux mappings
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
import seobject
import subprocess
from semanagePage import *;

##
## I18N
##
PROGNAME = "policycoreutils"
import gettext
gettext.bindtextdomain(PROGNAME, "/usr/share/locale")
gettext.textdomain(PROGNAME)
TYPE_COL = 0
PROTOCOL_COL = 1
MLS_COL = 2
PORT_COL = 3
try:
    gettext.install(PROGNAME,
                    localedir="/usr/share/locale",
                    unicode=False,
                    codeset = 'utf-8')
except IOError:
    import builtins
    builtins.__dict__['_'] = str

class portsPage(semanagePage):
    def __init__(self, xml):
        semanagePage.__init__(self, xml, "ports", _("Network Port"))
        xml.signal_connect("on_group_clicked", self.on_group_clicked)
        self.group = False
        self.ports_filter = xml.get_widget("portsFilterEntry")
        self.ports_filter.connect("focus_out_event", self.filter_changed)
        self.ports_filter.connect("activate", self.filter_changed)
        self.ports_name_entry = xml.get_widget("portsNameEntry")
        self.ports_protocol_combo = xml.get_widget("portsProtocolCombo")
        self.ports_number_entry = xml.get_widget("portsNumberEntry")
        self.ports_mls_entry = xml.get_widget("portsMLSEntry")
        self.ports_add_button = xml.get_widget("portsAddButton")
        self.ports_properties_button = xml.get_widget("portsPropertiesButton")
        self.ports_delete_button = xml.get_widget("portsDeleteButton")
        liststore = self.ports_protocol_combo.get_model()
        it = liststore.get_iter_first()
        self.ports_protocol_combo.set_active_iter(it)
        self.init_store()
        self.edit = True
        self.load()

    def filter_changed(self, *arg):
        filt =  arg[0].get_text()
        if filt != self.filter:
            if self.edit:
                self.load(filt)
            else:
                self.group_load(filt)

    def init_store(self):
        self.store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING , gobject.TYPE_STRING)
        self.view.set_model(self.store)
        self.store.set_sort_column_id(0, gtk.SORT_ASCENDING)

        self.view.set_search_equal_func(self.search)
        col = gtk.TreeViewColumn(_("SELinux Port\nType"), gtk.CellRendererText(), text = TYPE_COL)
        col.set_sort_column_id(TYPE_COL)
        col.set_resizable(True)
        self.view.append_column(col)
        self.store.set_sort_column_id(TYPE_COL, gtk.SORT_ASCENDING)

        col = gtk.TreeViewColumn(_("Protocol"), gtk.CellRendererText(), text = PROTOCOL_COL)
        col.set_sort_column_id(PROTOCOL_COL)
        col.set_resizable(True)
        self.view.append_column(col)

        self.mls_col = gtk.TreeViewColumn(_("MLS/MCS\nLevel"), gtk.CellRendererText(), text = MLS_COL)
        self.mls_col.set_resizable(True)
        self.mls_col.set_sort_column_id(MLS_COL)
        self.view.append_column(self.mls_col)

        col = gtk.TreeViewColumn(_("Port"), gtk.CellRendererText(), text = PORT_COL)
        col.set_sort_column_id(PORT_COL)
        col.set_resizable(True)
        self.view.append_column(col)
        self.store.set_sort_func(PORT_COL,self.sort_int, "")

    def sort_int(self, treemodel, iter1, iter2, user_data):
        try:
            p1 = int(treemodel.get_value(iter1,PORT_COL).split('-')[0])
            p2 = int(treemodel.get_value(iter2,PORT_COL).split('-')[0])
            if p1 > p2:
                return 1
            if p1 == p2:
                return 0
            return -1
        except:
            return 0

    def load(self,filt = ""):
        self.filter=filt
        self.port = seobject.portRecords()
        pdict = self.port.get_all(self.local)
        keys = list(pdict.keys())
        keys.sort()
        self.store.clear()
        for k in keys:
            if not (self.match(str(k[0]), filt) or self.match(pdict[k][0], filt) or self.match(k[2], filt) or self.match(pdict[k][1], filt) or self.match(pdict[k][1], filt)):
                continue
            it = self.store.append()
            if k[0] == k[1]:
                self.store.set_value(it, PORT_COL, k[0])
            else:
                rec = "%s-%s" % k[:2]
                self.store.set_value(it, PORT_COL, rec)
            self.store.set_value(it, TYPE_COL, pdict[k][0])
            self.store.set_value(it, PROTOCOL_COL, k[2])
            self.store.set_value(it, MLS_COL, pdict[k][1])
        self.view.get_selection().select_path ((0,))

    def group_load(self, filt = ""):
        self.filter=filt
        self.port = seobject.portRecords()
        pdict = self.port.get_all_by_type(self.local)
        keys = list(pdict.keys())
        keys.sort()
        self.store.clear()
        for k in keys:
            ports_string = ", ".join(pdict[k])
            if not (self.match(ports_string, filt) or self.match(k[0], filt) or self.match(k[1], filt) ):
                continue
            it = self.store.append()
            self.store.set_value(it, TYPE_COL, k[0])
            self.store.set_value(it, PROTOCOL_COL, k[1])
            self.store.set_value(it, PORT_COL, ports_string)
            self.store.set_value(it, MLS_COL, "")
        self.view.get_selection().select_path ((0,))

    def propertiesDialog(self):
        if self.edit:
            semanagePage.propertiesDialog(self)

    def dialogInit(self):
        store, it = self.view.get_selection().get_selected()
        self.ports_number_entry.set_text(store.get_value(it, PORT_COL))
        self.ports_number_entry.set_sensitive(False)
        self.ports_protocol_combo.set_sensitive(False)
        self.ports_name_entry.set_text(store.get_value(it, TYPE_COL))
        self.ports_mls_entry.set_text(store.get_value(it, MLS_COL))
        protocol = store.get_value(it, PROTOCOL_COL)
        liststore = self.ports_protocol_combo.get_model()
        it = liststore.get_iter_first()
        while it != None and liststore.get_value(it,0) != protocol:
            it = liststore.iter_next(it)
        if it != None:
            self.ports_protocol_combo.set_active_iter(it)

    def dialogClear(self):
        self.ports_number_entry.set_text("")
        self.ports_number_entry.set_sensitive(True)
        self.ports_protocol_combo.set_sensitive(True)
        self.ports_name_entry.set_text("")
        self.ports_mls_entry.set_text("s0")

    def delete(self):
        store, it = self.view.get_selection().get_selected()
        port = store.get_value(it, PORT_COL)
        protocol = store.get_value(it, 1)
        self.wait()
        cmd = "semanage port -d -p %s %s" % (protocol, port)
        try:
            subprocess.check_output(cmd,
                                    stderr=subprocess.STDOUT,
                                    shell=True)
            store.remove(it)
            self.view.get_selection().select_path ((0,))
        except subprocess.CalledProcessError as e:
            self.error(e.output)
        self.ready()

    def add(self):
        target = self.ports_name_entry.get_text().strip()
        mls = self.ports_mls_entry.get_text().strip()
        port_number = self.ports_number_entry.get_text().strip()
        if port_number == "":
            port_number = "1"
        for i in port_number.split("-"):
            if not i.isdigit():
                self.error(_("Port number \"%s\" is not valid.  0 < PORT_NUMBER < 65536 ") % port_number )
                return False
        list_model = self.ports_protocol_combo.get_model()
        it = self.ports_protocol_combo.get_active_iter()
        protocol = list_model.get_value(it,0)
        self.wait()
        cmd = "semanage port -a -p %s -r %s -t %s %s" % (protocol, mls, target, port_number)
        try:
            subprocess.check_output(cmd,
                                    stderr=subprocess.STDOUT,
                                    shell=True)
            it = self.store.append()
            self.store.set_value(it, TYPE_COL, target)
            self.store.set_value(it, PORT_COL, port_number)
            self.store.set_value(it, PROTOCOL_COL, protocol)
            self.store.set_value(it, MLS_COL, mls)
        except subprocess.CalledProcessError as e:
            self.error(e.output)
        self.ready()

    def modify(self):
        target = self.ports_name_entry.get_text().strip()
        mls = self.ports_mls_entry.get_text().strip()
        port_number = self.ports_number_entry.get_text().strip()
        list_model = self.ports_protocol_combo.get_model()
        it = self.ports_protocol_combo.get_active_iter()
        protocol = list_model.get_value(it,0)
        self.wait()
        cmd = "semanage port -m -p %s -r %s -t %s %s" % (protocol, mls, target, port_number)
        try:
            subprocess.check_output(cmd,
                                    stderr=subprocess.STDOUT,
                                    shell=True)
            store, it = self.view.get_selection().get_selected()
            self.store.set_value(it, TYPE_COL, target)
            self.store.set_value(it, PORT_COL, port_number)
            self.store.set_value(it, PROTOCOL_COL, protocol)
            self.store.set_value(it, MLS_COL, mls)
            self.ready()
            return True
        except subprocess.CalledProcessError as e:
            self.error(e.output)
            self.ready()
            return False

    def on_group_clicked(self, button):
        self.ports_add_button.set_sensitive(self.group)
        self.ports_properties_button.set_sensitive(self.group)
        self.ports_delete_button.set_sensitive(self.group)
        self.mls_col.set_visible(self.group)

        self.group = not self.group
        if self.group:
            button.set_label(_("List View"))
            self.group_load(self.filter)
        else:
            button.set_label(_("Group View"))
            self.load(self.filter)

        return True
