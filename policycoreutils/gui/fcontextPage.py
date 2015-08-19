## fcontextPage.py - show selinux mappings
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
from gi.repository import Gtk
import Gtk.glade
from gi.repository import GObject
import seobject
import subprocess
from semanagePage import *;

SPEC_COL = 0
TYPE_COL = 1
FTYPE_COL = 2

class context:
    def __init__(self, scontext):
        self.scontext = scontext
        con=scontext.split(":")
        self.type = con[0]
        if len(con) > 1:
            self.mls = con[1]
        else:
            self.mls = "s0"

    def __str__(self):
        return self.scontext

##
## I18N
##
PROGNAME="policycoreutils"

import gettext
gettext.bindtextdomain(PROGNAME, "/usr/share/locale")
gettext.textdomain(PROGNAME)
try:
    gettext.install(PROGNAME,
                    localedir="/usr/share/locale",
                    unicode=False,
                    codeset = 'utf-8')
except IOError:
    import builtins
    builtins.__dict__['_'] = str


class fcontextPage(semanagePage):
    def __init__(self, xml):
        semanagePage.__init__(self, xml, "fcontext", _("File Labeling"))
        self.fcontextFilter = xml.get_widget("fcontextFilterEntry")
        self.fcontextFilter.connect("focus_out_event", self.filter_changed)
        self.fcontextFilter.connect("activate", self.filter_changed)

        self.store = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_STRING)
        self.view = xml.get_widget("fcontextView")
        self.view.set_model(self.store)
        self.view.set_search_equal_func(self.search)

        col = Gtk.TreeViewColumn(_("File\nSpecification"), Gtk.CellRendererText(), text=SPEC_COL)
        col.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        col.set_fixed_width(250)

        col.set_sort_column_id(SPEC_COL)
        col.set_resizable(True)
        self.view.append_column(col)
        col = Gtk.TreeViewColumn(_("Selinux\nFile Type"), Gtk.CellRendererText(), text=TYPE_COL)

        col.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        col.set_fixed_width(250)
        col.set_sort_column_id(TYPE_COL)
        col.set_resizable(True)
        self.view.append_column(col)
        col = Gtk.TreeViewColumn(_("File\nType"), Gtk.CellRendererText(), text=2)
        col.set_sort_column_id(FTYPE_COL)
        col.set_resizable(True)
        self.view.append_column(col)

        self.store.set_sort_column_id(SPEC_COL, Gtk.SortType.ASCENDING)
        self.load()
        self.fcontextEntry = xml.get_widget("fcontextEntry")
        self.fcontextFileTypeCombo = xml.get_widget("fcontextFileTypeCombo")
        liststore=self.fcontextFileTypeCombo.get_model()
        for k in seobject.file_types:
            if len(k) > 0 and  k[0] != '-':
                it=liststore.append()
                liststore.set_value(it, 0, k)
        it = liststore.get_iter_first()
        self.fcontextFileTypeCombo.set_active_iter(it)
        self.fcontextTypeEntry = xml.get_widget("fcontextTypeEntry")
        self.fcontextMLSEntry = xml.get_widget("fcontextMLSEntry")

    def match(self, fcon_dict, k, filt):
        try:
            f=filt.lower()
            for con in k:
                k=con.lower()
                if k.find(f) >= 0:
                    return True
            for con in fcon_dict[k]:
                k=con.lower()
                if k.find(f) >= 0:
                    return True
        except:
            pass
        return False

    def load(self, filt=""):
        self.filter=filt
        self.fcontext=seobject.fcontextRecords()
        self.store.clear()
        fcon_dict=self.fcontext.get_all(self.local)
        keys = list(fcon_dict.keys())
        keys.sort()
        for k in keys:
            if not self.match(fcon_dict, k, filt):
                continue
            it=self.store.append()
            self.store.set_value(it, SPEC_COL, k[0])
            self.store.set_value(it, FTYPE_COL, k[1])
            if fcon_dict[k]:
                rec="%s:%s" % (fcon_dict[k][2], seobject.translate(fcon_dict[k][3],False))
            else:
                rec="<<None>>"
            self.store.set_value(it, TYPE_COL, rec)
        self.view.get_selection().select_path ((0,))

    def filter_changed(self, *arg):
        filt =  arg[0].get_text()
        if filt != self.filter:
            self.load(filt)

    def dialogInit(self):
        store, it = self.view.get_selection().get_selected()
        self.fcontextEntry.set_text(store.get_value(it, SPEC_COL))
        self.fcontextEntry.set_sensitive(False)
        scontext = store.get_value(it, TYPE_COL)
        scon=context(scontext)
        self.fcontextTypeEntry.set_text(scon.type)
        self.fcontextMLSEntry.set_text(scon.mls)
        setype=store.get_value(it, FTYPE_COL)
        liststore=self.fcontextFileTypeCombo.get_model()
        it = liststore.get_iter_first()
        while it != None and liststore.get_value(it,0) != setype:
            it = liststore.iter_next(it)
        if it != None:
            self.fcontextFileTypeCombo.set_active_iter(it)
        self.fcontextFileTypeCombo.set_sensitive(False)

    def dialogClear(self):
        self.fcontextEntry.set_text("")
        self.fcontextEntry.set_sensitive(True)
        self.fcontextFileTypeCombo.set_sensitive(True)
        self.fcontextTypeEntry.set_text("")
        self.fcontextMLSEntry.set_text("s0")

    def delete(self):
        store, it = self.view.get_selection().get_selected()
        fspec=store.get_value(it, SPEC_COL)
        ftype=store.get_value(it, FTYPE_COL)
        self.wait()
        try:
            subprocess.check_output("semanage fcontext -d -f '%s' '%s'" % (ftype, fspec),
                                    stderr=subprocess.STDOUT,
                                    shell=True)
            store.remove(it)
            self.view.get_selection().select_path ((0,))
        except subprocess.CalledProcessError as e:
            self.error(e.output)
        self.ready()

    def add(self):
        ftype=["", "--", "-d", "-c", "-b", "-s", "-l", "-p" ]
        fspec=self.fcontextEntry.get_text().strip()
        setype=self.fcontextTypeEntry.get_text().strip()
        mls=self.fcontextMLSEntry.get_text().strip()
        list_model=self.fcontextFileTypeCombo.get_model()
        active = self.fcontextFileTypeCombo.get_active()
        self.wait()
        try:
            subprocess.check_output("semanage fcontext -a -t %s -r %s -f '%s' '%s'" % (setype, mls, ftype[active], fspec),
                                    stderr=subprocess.STDOUT,
                                    shell=True)
            self.ready()
            it=self.store.append()
            self.store.set_value(it, SPEC_COL, fspec)
            self.store.set_value(it, FTYPE_COL, ftype)
            self.store.set_value(it, TYPE_COL, "%s:%s" % (setype, mls))
        except subprocess.CalledProcessError as e:
            self.error(e.output)
            self.ready()
            return False

    def modify(self):
        fspec=self.fcontextEntry.get_text().strip()
        setype=self.fcontextTypeEntry.get_text().strip()
        mls=self.fcontextMLSEntry.get_text().strip()
        list_model=self.fcontextFileTypeCombo.get_model()
        it = self.fcontextFileTypeCombo.get_active_iter()
        ftype=list_model.get_value(it,0)
        self.wait()
        try:
            subprocess.check_output("semanage fcontext -m -t %s -r %s -f '%s' '%s'" % (setype, mls, ftype, fspec),
                                    stderr=subprocess.STDOUT,
                                    shell=True)
            self.ready()
            store, it = self.view.get_selection().get_selected()
            self.store.set_value(it, SPEC_COL, fspec)
            self.store.set_value(it, FTYPE_COL, ftype)
            self.store.set_value(it, TYPE_COL, "%s:%s" % (setype, mls))
        except subprocess.CalledProcessError as e:
            self.error(e.output)
            self.ready()
            return False
