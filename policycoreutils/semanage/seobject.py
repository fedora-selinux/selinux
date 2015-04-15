#! /usr/bin/python -Es
# Copyright (C) 2005-2013 Red Hat
# see file 'COPYING' for use and warranty information
#
# semanage is a tool for managing SELinux configuration files
#
#    This program is free software; you can redistribute it and/or
#    modify it under the terms of the GNU General Public License as
#    published by the Free Software Foundation; either version 2 of
#    the License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA     
#                                        02111-1307  USA
#
#  

import pwd, grp, string, selinux, tempfile, os, re, sys, stat, shutil
from semanage import *;
PROGNAME = "policycoreutils"
import sepolicy
from sepolicy import boolean_desc, boolean_category, gen_bool_dict
gen_bool_dict()
from IPy import IP

import gettext
gettext.bindtextdomain(PROGNAME, "/usr/share/locale")
gettext.textdomain(PROGNAME)

import gettext
translation=gettext.translation(PROGNAME, localedir = "/usr/share/locale", fallback=True)
_=translation.ugettext

import syslog

file_types = {}
file_types[""] = SEMANAGE_FCONTEXT_ALL;
file_types["all files"] = SEMANAGE_FCONTEXT_ALL;
file_types["a"] = SEMANAGE_FCONTEXT_ALL;
file_types["regular file"] = SEMANAGE_FCONTEXT_REG;
file_types["--"] = SEMANAGE_FCONTEXT_REG;
file_types["f"] = SEMANAGE_FCONTEXT_REG;
file_types["-d"] = SEMANAGE_FCONTEXT_DIR;
file_types["directory"] = SEMANAGE_FCONTEXT_DIR;
file_types["d"] = SEMANAGE_FCONTEXT_DIR;
file_types["-c"] = SEMANAGE_FCONTEXT_CHAR;
file_types["character device"] = SEMANAGE_FCONTEXT_CHAR;
file_types["c"] = SEMANAGE_FCONTEXT_CHAR;
file_types["-b"] = SEMANAGE_FCONTEXT_BLOCK;
file_types["block device"] = SEMANAGE_FCONTEXT_BLOCK;
file_types["b"] = SEMANAGE_FCONTEXT_BLOCK;
file_types["-s"] = SEMANAGE_FCONTEXT_SOCK;
file_types["socket"] = SEMANAGE_FCONTEXT_SOCK;
file_types["s"] = SEMANAGE_FCONTEXT_SOCK;
file_types["-l"] = SEMANAGE_FCONTEXT_LINK;
file_types["l"] = SEMANAGE_FCONTEXT_LINK;
file_types["symbolic link"] = SEMANAGE_FCONTEXT_LINK;
file_types["p"] = SEMANAGE_FCONTEXT_PIPE;
file_types["-p"] = SEMANAGE_FCONTEXT_PIPE;
file_types["named pipe"] = SEMANAGE_FCONTEXT_PIPE;

file_type_str_to_option = { "all files": "a",
                            "regular file":"f",
                            "directory":"d",
                            "character device":"c",
                            "block device":"b",
                            "socket file":"s",
                            "symbolic link":"l",
                            "named pipe":"p" }
try:
	import audit
	class logger:
		def __init__(self):
			self.audit_fd = audit.audit_open()
			self.log_list = []
		def log(self, msg, name = "", sename = "", serole = "", serange = "", oldsename = "", oldserole = "", oldserange = ""):
			
			sep = "-"
			if sename != oldsename:
				msg += sep + "sename"; sep = ","
			if serole != oldserole:
				msg += sep + "role"; sep = ","
			if serange != oldserange:
				msg += sep + "range"; sep = ","

			self.log_list.append([self.audit_fd, audit.AUDIT_ROLE_ASSIGN, sys.argv[0], str(msg), name, 0, sename, serole, serange, oldsename, oldserole, oldserange, "", "", ""])

		def log_remove(self, msg, name = "", sename = "", serole = "", serange = "", oldsename = "", oldserole = "", oldserange = ""):
			self.log_list.append([self.audit_fd, audit.AUDIT_ROLE_REMOVE, sys.argv[0], str(msg), name, 0, sename, serole, serange, oldsename, oldserole, oldserange, "", "", ""])

		def commit(self,success):
			for l in self.log_list:
				audit.audit_log_semanage_message(*(l + [success]))
			self.log_list = []
except:
	class logger:
		def __init__(self):
			self.log_list=[]

		def log(self, msg, name = "", sename = "", serole = "", serange = "", oldsename = "", oldserole = "", oldserange = ""):
			message = " %s name=%s" % (msg, name)
			if sename != "":
				message += " sename=" + sename
			if oldsename != "":
				message += " oldsename=" + oldsename
			if serole != "":
				message += " role=" + serole
			if oldserole != "":
				message += " old_role=" + oldserole
			if serange != "" and serange != None:
				message += " MLSRange=" + serange
			if oldserange != "" and oldserange != None:
				message += " old_MLSRange=" + oldserange
			self.log_list.append(message)

		def log_remove(self, msg, name = "", sename = "", serole = "", serange = "", oldsename = "", oldserole = "", oldserange = ""):
			self.log(msg, name, sename, serole, serange, oldsename, oldserole, oldserange)

		def commit(self,success):
			if success == 1:
				message = "Successful: "
			else:
				message = "Failed: "
			for l in self.log_list:
				syslog.syslog(syslog.LOG_INFO, message + l)

class nulllogger:
	def log(self, msg, name = "", sename = "", serole = "", serange = "", oldsename = "", oldserole = "", oldserange = ""):
		pass

	def log_remove(self, msg, name = "", sename = "", serole = "", serange = "", oldsename = "", oldserole = "", oldserange = ""):
		pass

	def commit(self,success):
		pass

def validate_level(raw):
	sensitivity = "s[0-9]*"
	category = "c[0-9]*"
	cat_range = category + "(\." + category +")?"
	categories = cat_range + "(\," + cat_range + ")*"
	reg = sensitivity + "(-" + sensitivity + ")?" + "(:" + categories + ")?"
	return re.search("^" + reg +"$", raw)

def translate(raw, prepend = 1):
        filler = "a:b:c:"
        if prepend == 1:
		context = "%s%s" % (filler, raw)
	else:
		context = raw
	(rc, trans) = selinux.selinux_raw_to_trans_context(context)
	if rc != 0:
		return raw
	if prepend:
		trans = trans[len(filler):]
	if trans == "":
		return raw
	else:
		return trans
	
def untranslate(trans, prepend = 1):
        filler = "a:b:c:"
 	if prepend == 1:
		context = "%s%s" % (filler, trans)
	else:
		context = trans

	(rc, raw) = selinux.selinux_trans_to_raw_context(context)
	if rc != 0:
		return trans
	if prepend:
		raw = raw[len(filler):]
	if raw == "":
		return trans
	else:
		return raw

class semanageRecords:
        transaction = False
        handle = None
        store = None
        def __init__(self, store):
               global handle
	       self.load = True
               self.sh = self.get_handle(store)

	       rc, localstore = selinux.selinux_getpolicytype()
	       if store == "" or store == localstore:
		       self.mylog = logger()	
	       else:
		       self.mylog = nulllogger()	

	def set_reload(self, load):
	       self.load = load

        def get_handle(self, store):
		global is_mls_enabled

		if semanageRecords.handle:
			return semanageRecords.handle

		handle = semanage_handle_create()
		if not handle:
			raise ValueError(_("Could not create semanage handle"))

		if not semanageRecords.transaction and store != "":
			semanage_select_store(handle, store, SEMANAGE_CON_DIRECT);
			semanageRecords.store = store

		if not semanage_is_managed(handle):
			semanage_handle_destroy(handle)
			raise ValueError(_("SELinux policy is not managed or store cannot be accessed."))

		rc = semanage_access_check(handle)
		if rc < SEMANAGE_CAN_READ:
			semanage_handle_destroy(handle)
			raise ValueError(_("Cannot read policy store."))

		rc = semanage_connect(handle)
		if rc < 0:
			semanage_handle_destroy(handle)
			raise ValueError(_("Could not establish semanage connection"))

		is_mls_enabled = semanage_mls_enabled(handle)
		if is_mls_enabled < 0:
			semanage_handle_destroy(handle)
			raise ValueError(_("Could not test MLS enabled status"))

		semanageRecords.handle = handle
		return semanageRecords.handle

        def deleteall(self):
               raise ValueError(_("Not yet implemented"))

        def start(self):
               if semanageRecords.transaction:
                      raise ValueError(_("Semanage transaction already in progress"))
               self.begin()
               semanageRecords.transaction = True

        def begin(self):
               if semanageRecords.transaction:
                      return
               rc = semanage_begin_transaction(self.sh)
               if rc < 0:
                      raise ValueError(_("Could not start semanage transaction"))
        def customized(self):
               raise ValueError(_("Not yet implemented"))

        def commit(self):
		if semanageRecords.transaction:
			return

		semanage_set_reload(self.sh, self.load)
		rc = semanage_commit(self.sh) 
		if rc < 0:
			self.mylog.commit(0)
			raise ValueError(_("Could not commit semanage transaction"))
		self.mylog.commit(1)

        def finish(self):
               if not semanageRecords.transaction:
                      raise ValueError(_("Semanage transaction not in progress"))
               semanageRecords.transaction = False
               self.commit()

class moduleRecords(semanageRecords):
	def __init__(self, store):
	       semanageRecords.__init__(self, store)

	def get_all(self):
               l = []
               (rc, mlist, number) = semanage_module_list_all(self.sh)
               if rc < 0:
                      raise ValueError(_("Could not list SELinux modules"))

               for i in range(number):
                      mod = semanage_module_list_nth(mlist, i)

                      rc, name = semanage_module_info_get_name(self.sh, mod)
                      if rc < 0:
                          raise ValueError(_("Could not get module name"))

                      rc, enabled = semanage_module_info_get_enabled(self.sh, mod)
                      if rc < 0:
                          raise ValueError(_("Could not get module enabled"))

                      rc, priority = semanage_module_info_get_priority(self.sh, mod)
                      if rc < 0:
                          raise ValueError(_("Could not get module priority"))

                      rc, lang_ext = semanage_module_info_get_lang_ext(self.sh, mod)
                      if rc < 0:
                          raise ValueError(_("Could not get module lang_ext"))

                      l.append((name, enabled, priority, lang_ext))

               # sort the list so they are in name order, but with higher priorities coming first
               l.sort(key = lambda t: t[3], reverse=True)
               l.sort(key = lambda t: t[0])
               return l

        def customized(self):
		all = self.get_all()
		if len(all) == 0:
			return
                return map(lambda x: "-d %s" % x[0], filter(lambda t: t[1] == 0, all))

	def list(self, heading = 1, locallist = 0):
		all = self.get_all()
		if len(all) == 0:
			return 

		if heading:
			print "\n%-25s %-9s %s\n" % (_("Module Name"), _("Priority"), _("Language"))
                for t in all:
                       if t[1] == 0:
                              disabled = _("Disabled")
                       else:
                              if locallist:
                                      continue
                              disabled = ""
                       print "%-25s %-9s %-5s %s" % (t[0], t[2], t[3], disabled)

	def add(self, file, priority):
               if not os.path.exists(file):
                       raise ValueError(_("Module does not exists %s ") % file)

               rc = semanage_set_default_priority(self.sh, priority)
               if rc < 0:
                       raise ValueError(_("Invalid priority %d (needs to be between 1 and 999)") % priority)

               rc = semanage_module_install_file(self.sh, file);
               if rc >= 0:
                      self.commit()

	def set_enabled(self, module, enable):
               for m in module.split():
                      rc, key = semanage_module_key_create(self.sh)
                      if rc < 0:
                              raise ValueError(_("Could not create module key"))

                      rc = semanage_module_key_set_name(self.sh, key, m)
                      if rc < 0:
                              raise ValueError(_("Could not set module key name"))

                      rc = semanage_module_set_enabled(self.sh, key, enable)
                      if rc < 0:
                              if enable:
                                  raise ValueError(_("Could not enable module %s") % m)
                              else:
                                  raise ValueError(_("Could not disable module %s") % m)
               self.commit()

	def modify(self, file):
               rc = semanage_module_update_file(self.sh, file);
               if rc >= 0:
                      self.commit()

	def delete(self, module, priority):
               rc = semanage_set_default_priority(self.sh, priority)
               if rc < 0:
                       raise ValueError(_("Invalid priority %d (needs to be between 1 and 999)") % priority)

               for m in module.split():
                      rc = semanage_module_remove(self.sh, m)
                      if rc < 0 and rc != -2:
                             raise ValueError(_("Could not remove module %s (remove failed)") % m)

               self.commit()

	def deleteall(self):
                l = map(lambda x: x[0], filter(lambda t: t[1] == 0, self.get_all()))
                for m in l:
                        self.enable(m)

class dontauditClass(semanageRecords):
	def __init__(self, store):
               semanageRecords.__init__(self, store)

	def toggle(self, dontaudit):
               if dontaudit not in [ "on", "off" ]:
                      raise ValueError(_("dontaudit requires either 'on' or 'off'"))
               self.begin()
               rc = semanage_set_disable_dontaudit(self.sh, dontaudit == "off")
               self.commit()
               
class permissiveRecords(semanageRecords):
	def __init__(self, store):
               semanageRecords.__init__(self, store)

	def get_all(self):
               l = []
               (rc, mlist, number) = semanage_module_list(self.sh)
               if rc < 0:
                      raise ValueError(_("Could not list SELinux modules"))

               for i in range(number):
                      mod = semanage_module_list_nth(mlist, i)
                      name = semanage_module_get_name(mod)
                      if name and name.startswith("permissive_"):
                             l.append(name.split("permissive_")[1])
               return l

	def list(self, heading = 1, locallist = 0):
		all = map(lambda y: y["name"], filter(lambda x: x["permissive"], sepolicy.info(sepolicy.TYPE)))
		if len(all) == 0:
			return 

		if heading:
			print "\n%-25s\n" % (_("Builtin Permissive Types"))
		customized = self.get_all()
                for t in all:
			if t not in customized:
				print t

		if len(customized) == 0:
			return 

		if heading:
			print "\n%-25s\n" % (_("Customized Permissive Types"))
		for t in customized:
			print t

	def add(self, type):
               import glob
	       try:
		       import sepolgen.module as module
	       except ImportError:
		       raise ValueError(_("The sepolgen python module is required to setup permissive domains.\nIn some distributions it is included in the policycoreutils-devel patckage.\n# yum install policycoreutils-devel\nOr similar for your distro."))
		
               name = "permissive_%s" % type
               modtxt = "(typepermissive %s)" % type

               rc = semanage_module_install(self.sh, modtxt, len(modtxt), name, "cil");
               if rc >= 0:
                      self.commit()

               if rc < 0:
			raise ValueError(_("Could not set permissive domain %s (module installation failed)") % name)

	def delete(self, name):
               for n in name.split():
                      rc = semanage_module_remove(self.sh, "permissive_%s" % n)
                      if rc < 0:
                             raise ValueError(_("Could not remove permissive domain %s (remove failed)") % name)
                      
               self.commit()
			
	def deleteall(self):
               l = self.get_all()
               if len(l) > 0:
                      all = " ".join(l)
                      self.delete(all)

class loginRecords(semanageRecords):
	def __init__(self, store = ""):
		semanageRecords.__init__(self, store)
		self.oldsename  = None
		self.oldserange = None
		self.sename  = None
		self.serange = None

	def __add(self, name, sename, serange):
		rec, self.oldsename, self.oldserange = selinux.getseuserbyname(name)
		if sename == "":
			sename = "user_u"
			
		userrec = seluserRecords()
		range, (rc, oldserole) = userrec.get(self.oldsename)
		range, (rc, serole) = userrec.get(sename)

		if is_mls_enabled == 1:
			if serange != "":
				serange = untranslate(serange)
			else:
                           serange = range
			
		(rc, k) = semanage_seuser_key_create(self.sh, name)
		if rc < 0:
			raise ValueError(_("Could not create a key for %s") % name)

		(rc, exists) = semanage_seuser_exists(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not check if login mapping for %s is defined") % name)
		if exists:
			raise ValueError(_("Login mapping for %s is already defined") % name)
                if name[0] == '%':
                       try:
                              grp.getgrnam(name[1:])
                       except:
                              raise ValueError(_("Linux Group %s does not exist") % name[1:])
                else:
                       try:
                              pwd.getpwnam(name)
                       except:
                              raise ValueError(_("Linux User %s does not exist") % name)

                (rc, u) = semanage_seuser_create(self.sh)
                if rc < 0:
                       raise ValueError(_("Could not create login mapping for %s") % name)

                rc = semanage_seuser_set_name(self.sh, u, name)
                if rc < 0:
                       raise ValueError(_("Could not set name for %s") % name)

                if (is_mls_enabled == 1) and (serange != ""):
                       rc = semanage_seuser_set_mlsrange(self.sh, u, serange)
                       if rc < 0:
                              raise ValueError(_("Could not set MLS range for %s") % name)

                rc = semanage_seuser_set_sename(self.sh, u, sename)
                if rc < 0:
                       raise ValueError(_("Could not set SELinux user for %s") % name)

                rc = semanage_seuser_modify_local(self.sh, k, u)
                if rc < 0:
                       raise ValueError(_("Could not add login mapping for %s") % name)

		semanage_seuser_key_free(k)
		semanage_seuser_free(u)
		self.mylog.log("login", name, sename=sename, serange=serange, serole=",".join(serole), oldserole=",".join(oldserole), oldsename=self.oldsename, oldserange=self.oldserange);

	def add(self, name, sename, serange):
		try:
			self.begin()
			self.__add(name, sename, serange)
			self.commit()
		except ValueError, error:
			self.mylog.commit(0)
			raise error

	def __modify(self, name, sename = "", serange = ""):
		rec, self.oldsename, self.oldserange = selinux.getseuserbyname(name)
		if sename == "" and serange == "":
                      raise ValueError(_("Requires seuser or serange"))

		userrec = seluserRecords()
		range, (rc, oldserole) = userrec.get(self.oldsename)

		if sename != "":
			range, (rc, serole) = userrec.get(sename)
		else:
			serole=oldserole

		if serange != "":
			self.serange=serange
		else:
			self.serange=range

		(rc, k) = semanage_seuser_key_create(self.sh, name)
		if rc < 0:
		       raise ValueError(_("Could not create a key for %s") % name)

		(rc, exists) = semanage_seuser_exists(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not check if login mapping for %s is defined") % name)
		if not exists:
			raise ValueError(_("Login mapping for %s is not defined") % name)
		
		(rc, u) = semanage_seuser_query(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not query seuser for %s") % name)
		
		self.oldserange = semanage_seuser_get_mlsrange(u)
		self.oldsename = semanage_seuser_get_sename(u)
		if (is_mls_enabled == 1) and (serange != ""):
			semanage_seuser_set_mlsrange(self.sh, u, untranslate(serange))

		if sename != "":
			semanage_seuser_set_sename(self.sh, u, sename)
		else:
			self.sename = self.oldsename
			
		rc = semanage_seuser_modify_local(self.sh, k, u)
		if rc < 0:
			raise ValueError(_("Could not modify login mapping for %s") % name)

		semanage_seuser_key_free(k)
		semanage_seuser_free(u)
		self.mylog.log("login", name,sename=self.sename,serange=self.serange, serole=",".join(serole), oldserole=",".join(oldserole), oldsename=self.oldsename, oldserange=self.oldserange);

	def modify(self, name, sename = "", serange = ""):
		try:
                        self.begin()
                        self.__modify(name, sename, serange)
                        self.commit()
		except ValueError, error:
			self.mylog.commit(0)
			raise error

	def __delete(self, name):
		rec, self.oldsename, self.oldserange = selinux.getseuserbyname(name)
		userrec = seluserRecords()
		range, (rc, oldserole) = userrec.get(self.oldsename)

		(rc, k) = semanage_seuser_key_create(self.sh, name)
		if rc < 0:
			raise ValueError(_("Could not create a key for %s") % name)

		(rc, exists) = semanage_seuser_exists(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not check if login mapping for %s is defined") % name)
		if not exists:
			raise ValueError(_("Login mapping for %s is not defined") % name)
		
		(rc, exists) = semanage_seuser_exists_local(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not check if login mapping for %s is defined") % name)
		if not exists:
			raise ValueError(_("Login mapping for %s is defined in policy, cannot be deleted") % name)
		
		rc = semanage_seuser_del_local(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not delete login mapping for %s") % name)
		
		semanage_seuser_key_free(k)

		rec, self.sename, self.serange = selinux.getseuserbyname("__default__")
		range, (rc, serole) = userrec.get(self.sename)

		self.mylog.log_remove("login", name, sename=self.sename, serange=self.serange, serole=",".join(serole), oldserole=",".join(oldserole), oldsename=self.oldsename, oldserange=self.oldserange);

	def delete(self, name):
		try:
			self.begin()
			self.__delete(name)
			self.commit()

		except ValueError, error:
			self.mylog.commit(0)
			raise error
		
	def deleteall(self):
		(rc, ulist) = semanage_seuser_list_local(self.sh)
		if rc < 0:
			raise ValueError(_("Could not list login mappings"))

		try:
			self.begin()
			for u in ulist:
				self.__delete(semanage_seuser_get_name(u))
			self.commit()
		except ValueError, error:
			self.mylog.commit(0)
			raise error
		
	def get_all_logins(self):
		ddict = {}
		self.logins_path = selinux.selinux_policy_root() + "/logins"
		for path,dirs,files in os.walk(self.logins_path):
			if path == self.logins_path:
				for name in files:
					try:
						fd = open(path + "/" + name)
						rec = fd.read().rstrip().split(":")
						fd.close()
						ddict[name] = (rec[1], rec[2], rec[0])
					except IndexError:
						pass
		return ddict

	def get_all(self, locallist = 0):
		ddict = {}
                if locallist:
                       (rc, self.ulist) = semanage_seuser_list_local(self.sh)
                else:
                       (rc, self.ulist) = semanage_seuser_list(self.sh)
		if rc < 0:
			raise ValueError(_("Could not list login mappings"))

		for u in self.ulist:
			name = semanage_seuser_get_name(u)
			ddict[name] = (semanage_seuser_get_sename(u), semanage_seuser_get_mlsrange(u), "*")
		return ddict

        def customized(self):
                l = []
                ddict = self.get_all(True)
                keys = ddict.keys()
                keys.sort()
                for k in keys:
                       l.append("-a -s %s -r '%s' %s" % (ddict[k][0], ddict[k][1], k))
                return l

	def list(self,heading = 1, locallist = 0):
		ddict = self.get_all(locallist)
		ldict = self.get_all_logins()
		lkeys = ldict.keys()
		keys = ddict.keys()
		if len(keys) == 0 and len(lkeys) == 0:
			return 
		keys.sort()
		lkeys.sort()

		if is_mls_enabled == 1:
			if heading:
				print "\n%-20s %-20s %-20s %s\n" % (_("Login Name"), _("SELinux User"), _("MLS/MCS Range"), _("Service"))
			for k in keys:
				u = ddict[k]
				print "%-20s %-20s %-20s %s" % (k, u[0], translate(u[1]), u[2])
			if len(lkeys):
				print "\nLocal customization in %s" % self.logins_path
				
			for k in lkeys:
				u = ldict[k]
				print "%-20s %-20s %-20s %s" % (k, u[0], translate(u[1]), u[2])
		else:
			if heading:
				print "\n%-25s %-25s\n" % (_("Login Name"), _("SELinux User"))
			for k in keys:
				print "%-25s %-25s" % (k, ddict[k][0])

class seluserRecords(semanageRecords):
	def __init__(self, store = ""):
		semanageRecords.__init__(self, store)

	def get(self, name):
                (rc, k) = semanage_user_key_create(self.sh, name)
                if rc < 0:
                       raise ValueError(_("Could not create a key for %s") % name)
                (rc, exists) = semanage_user_exists(self.sh, k)
                if rc < 0:
                       raise ValueError(_("Could not check if SELinux user %s is defined") % name)
                (rc, u) = semanage_user_query(self.sh, k)
                if rc < 0:
                       raise ValueError(_("Could not query user for %s") % name)
                serange = semanage_user_get_mlsrange(u)
                serole = semanage_user_get_roles(self.sh,u)
		semanage_user_key_free(k)
		semanage_user_free(u)
		return serange, serole
                
	def __add(self, name, roles, selevel, serange, prefix):
		if is_mls_enabled == 1:
			if serange == "":
				serange = "s0"
			else:
				serange = untranslate(serange)
			
			if selevel == "":
				selevel = "s0"
			else:
				selevel = untranslate(selevel)
			
                if len(roles) < 1:
                       raise ValueError(_("You must add at least one role for %s") % name)
                       
                (rc, k) = semanage_user_key_create(self.sh, name)
                if rc < 0:
                       raise ValueError(_("Could not create a key for %s") % name)

                (rc, exists) = semanage_user_exists(self.sh, k)
                if rc < 0:
                       raise ValueError(_("Could not check if SELinux user %s is defined") % name)
                if exists:
                       raise ValueError(_("SELinux user %s is already defined") % name)

                (rc, u) = semanage_user_create(self.sh)
                if rc < 0:
                       raise ValueError(_("Could not create SELinux user for %s") % name)

                rc = semanage_user_set_name(self.sh, u, name)
                if rc < 0:
                       raise ValueError(_("Could not set name for %s") % name)

                for r in roles:
                       rc = semanage_user_add_role(self.sh, u, r)
                       if rc < 0:
                              raise ValueError(_("Could not add role %s for %s") % (r, name))

                if is_mls_enabled == 1:
                       rc = semanage_user_set_mlsrange(self.sh, u, serange)
                       if rc < 0:
                              raise ValueError(_("Could not set MLS range for %s") % name)

                       rc = semanage_user_set_mlslevel(self.sh, u, selevel)
                       if rc < 0:
                              raise ValueError(_("Could not set MLS level for %s") % name)
                rc = semanage_user_set_prefix(self.sh, u, prefix)
                if rc < 0:
                       raise ValueError(_("Could not add prefix %s for %s") % (r, prefix))
                (rc, key) = semanage_user_key_extract(self.sh,u)
                if rc < 0:
                       raise ValueError(_("Could not extract key for %s") % name)

                rc = semanage_user_modify_local(self.sh, k, u)
                if rc < 0:
                       raise ValueError(_("Could not add SELinux user %s") % name)

                semanage_user_key_free(k)
                semanage_user_free(u)
		self.mylog.log("seuser", sename=name, serole=",".join(roles), serange=serange)

	def add(self, name, roles, selevel, serange, prefix):
		serole = " ".join(roles)
		try:
			self.begin()
			self.__add( name, roles, selevel, serange, prefix)
			self.commit()
		except ValueError, error:
			self.mylog.commit(0)
			raise error

        def __modify(self, name, roles = [], selevel = "", serange = "", prefix = ""):
		oldserole = ""
		oldserange = ""
		newroles = string.join(roles, ' ');
                if prefix == "" and len(roles) == 0  and serange == "" and selevel == "":
                       if is_mls_enabled == 1:
                              raise ValueError(_("Requires prefix, roles, level or range"))
                       else:
                              raise ValueError(_("Requires prefix or roles"))

                (rc, k) = semanage_user_key_create(self.sh, name)
                if rc < 0:
                       raise ValueError(_("Could not create a key for %s") % name)

                (rc, exists) = semanage_user_exists(self.sh, k)
                if rc < 0:
                       raise ValueError(_("Could not check if SELinux user %s is defined") % name)
                if not exists:
                       raise ValueError(_("SELinux user %s is not defined") % name)

                (rc, u) = semanage_user_query(self.sh, k)
                if rc < 0:
                       raise ValueError(_("Could not query user for %s") % name)

                oldserange = semanage_user_get_mlsrange(u)
                (rc, rlist) = semanage_user_get_roles(self.sh, u)
                if rc >= 0:
                       oldserole = string.join(rlist, ' ');

                if (is_mls_enabled == 1) and (serange != ""):
                       semanage_user_set_mlsrange(self.sh, u, untranslate(serange))
                if (is_mls_enabled == 1) and (selevel != ""):
                       semanage_user_set_mlslevel(self.sh, u, untranslate(selevel))

                if prefix != "":
                       semanage_user_set_prefix(self.sh, u, prefix)

                if len(roles) != 0:
                       for r in rlist:
                              if r not in roles:
                                     semanage_user_del_role(u, r)
                       for r in roles:
                              if r not in rlist:
                                     semanage_user_add_role(self.sh, u, r)

                rc = semanage_user_modify_local(self.sh, k, u)
                if rc < 0:
                       raise ValueError(_("Could not modify SELinux user %s") % name)

		semanage_user_key_free(k)
		semanage_user_free(u)
	
		role=",".join(newroles.split())
		oldserole=",".join(oldserole.split())
		self.mylog.log("seuser", sename=name, oldsename=name, serole=role, serange=serange, oldserole=oldserole, oldserange=oldserange)


	def modify(self, name, roles = [], selevel = "", serange = "", prefix = ""):
		try:
                        self.begin()
                        self.__modify(name, roles, selevel, serange, prefix)
                        self.commit()
		except ValueError, error:
			self.mylog.commit(0)
			raise error

	def __delete(self, name):
               (rc, k) = semanage_user_key_create(self.sh, name)
               if rc < 0:
                      raise ValueError(_("Could not create a key for %s") % name)
			
               (rc, exists) = semanage_user_exists(self.sh, k)
               if rc < 0:
                      raise ValueError(_("Could not check if SELinux user %s is defined") % name)		
               if not exists:
                      raise ValueError(_("SELinux user %s is not defined") % name)

               (rc, exists) = semanage_user_exists_local(self.sh, k)
               if rc < 0:
                      raise ValueError(_("Could not check if SELinux user %s is defined") % name)
               if not exists:
                      raise ValueError(_("SELinux user %s is defined in policy, cannot be deleted") % name)
			
	       (rc, u) = semanage_user_query(self.sh, k)
	       if rc < 0:
                       raise ValueError(_("Could not query user for %s") % name)
	       oldserange = semanage_user_get_mlsrange(u)
	       (rc, rlist) = semanage_user_get_roles(self.sh, u)
	       oldserole = ",".join(rlist)

               rc = semanage_user_del_local(self.sh, k)
               if rc < 0:
                      raise ValueError(_("Could not delete SELinux user %s") % name)

               semanage_user_key_free(k)		
	       semanage_user_free(u)

	       self.mylog.log_remove("seuser", oldsename=name, oldserange=oldserange, oldserole=oldserole)

	def delete(self, name):
		try:
                        self.begin()
                        self.__delete(name)
                        self.commit()

		except ValueError, error:
			self.mylog.commit(0)
			raise error
		
	def deleteall(self):
		(rc, ulist) = semanage_user_list_local(self.sh)
		if rc < 0:
			raise ValueError(_("Could not list login mappings"))

		try:
			self.begin()
			for u in ulist:
				self.__delete(semanage_user_get_name(u))
			self.commit()
		except ValueError, error:
			self.mylog.commit(0)
			raise error

	def get_all(self, locallist = 0):
		ddict = {}
                if locallist:
                       (rc, self.ulist) = semanage_user_list_local(self.sh)
                else:
                       (rc, self.ulist) = semanage_user_list(self.sh)
		if rc < 0:
			raise ValueError(_("Could not list SELinux users"))

		for u in self.ulist:
			name = semanage_user_get_name(u)
			(rc, rlist) = semanage_user_get_roles(self.sh, u)
			if rc < 0:
				raise ValueError(_("Could not list roles for user %s") % name)

			roles = string.join(rlist, ' ');
			ddict[semanage_user_get_name(u)] = (semanage_user_get_prefix(u), semanage_user_get_mlslevel(u), semanage_user_get_mlsrange(u), roles)

		return ddict

        def customized(self):
                l = []
                ddict = self.get_all(True)
                keys = ddict.keys()
                keys.sort()
                for k in keys:
                       l.append("-a -L %s -r %s -R '%s' %s" % (ddict[k][1], ddict[k][2], ddict[k][3], k))
                return l

	def list(self, heading = 1, locallist = 0):
		ddict = self.get_all(locallist)
		keys = ddict.keys()
		if len(keys) == 0:
			return 
		keys.sort()

		if is_mls_enabled == 1:
			if heading:
				print "\n%-15s %-10s %-10s %-30s" % ("", _("Labeling"), _("MLS/"), _("MLS/"))
				print "%-15s %-10s %-10s %-30s %s\n" % (_("SELinux User"), _("Prefix"), _("MCS Level"), _("MCS Range"), _("SELinux Roles"))
			for k in keys:
				print "%-15s %-10s %-10s %-30s %s" % (k, ddict[k][0], translate(ddict[k][1]), translate(ddict[k][2]), ddict[k][3])
		else:
			if heading:
				print "%-15s %s\n" % (_("SELinux User"), _("SELinux Roles"))
			for k in keys:
				print "%-15s %s" % (k, ddict[k][3])

class portRecords(semanageRecords):
	try:
		valid_types =  sepolicy.info(sepolicy.ATTRIBUTE,"port_type")[0]["types"]
	except RuntimeError:
		valid_types = []

	def __init__(self, store = ""):
		semanageRecords.__init__(self, store)

	def __genkey(self, port, proto):
		if proto == "tcp":
			proto_d = SEMANAGE_PROTO_TCP
		else:
			if proto == "udp":
				proto_d = SEMANAGE_PROTO_UDP
			else:
				raise ValueError(_("Protocol udp or tcp is required"))
		if port == "":
			raise ValueError(_("Port is required"))
			
		ports = port.split("-")
		if len(ports) == 1:
			high = low = int(ports[0])
		else:
			low = int(ports[0])
			high = int(ports[1])

		if high > 65535:
			raise ValueError(_("Invalid Port"))

		(rc, k) = semanage_port_key_create(self.sh, low, high, proto_d)
		if rc < 0:
			raise ValueError(_("Could not create a key for %s/%s") % (proto, port))
		return ( k, proto_d, low, high )

	def __add(self, port, proto, serange, type):
		if is_mls_enabled == 1:
			if serange == "":
				serange = "s0"
			else:
				serange = untranslate(serange)
			
		if type == "":
			raise ValueError(_("Type is required"))

		if type not in self.valid_types:
			raise ValueError(_("Type %s is invalid, must be a port type") % type)

		( k, proto_d, low, high ) = self.__genkey(port, proto)			

		(rc, exists) = semanage_port_exists(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not check if port %s/%s is defined") % (proto, port))
		if exists:
			raise ValueError(_("Port %s/%s already defined") % (proto, port))

		(rc, p) = semanage_port_create(self.sh)
		if rc < 0:
			raise ValueError(_("Could not create port for %s/%s") % (proto, port))
		
		semanage_port_set_proto(p, proto_d)
		semanage_port_set_range(p, low, high)
		(rc, con) = semanage_context_create(self.sh)
		if rc < 0:
			raise ValueError(_("Could not create context for %s/%s") % (proto, port))

		rc = semanage_context_set_user(self.sh, con, "system_u")
		if rc < 0:
			raise ValueError(_("Could not set user in port context for %s/%s") % (proto, port))

		rc = semanage_context_set_role(self.sh, con, "object_r")
		if rc < 0:
			raise ValueError(_("Could not set role in port context for %s/%s") % (proto, port))

		rc = semanage_context_set_type(self.sh, con, type)
		if rc < 0:
			raise ValueError(_("Could not set type in port context for %s/%s") % (proto, port))

		if (is_mls_enabled == 1) and (serange != ""):
			rc = semanage_context_set_mls(self.sh, con, serange)
			if rc < 0:
				raise ValueError(_("Could not set mls fields in port context for %s/%s") % (proto, port))

		rc = semanage_port_set_con(self.sh, p, con)
		if rc < 0:
			raise ValueError(_("Could not set port context for %s/%s") % (proto, port))

		rc = semanage_port_modify_local(self.sh, k, p)
		if rc < 0:
			raise ValueError(_("Could not add port %s/%s") % (proto, port))
	
		semanage_context_free(con)
		semanage_port_key_free(k)
		semanage_port_free(p)

	def add(self, port, proto, serange, type):
                self.begin()
                self.__add(port, proto, serange, type)
                self.commit()

	def __modify(self, port, proto, serange, setype):
		if serange == "" and setype == "":
			if is_mls_enabled == 1:
				raise ValueError(_("Requires setype or serange"))
			else:
				raise ValueError(_("Requires setype"))

		if setype and setype not in self.valid_types:
			raise ValueError(_("Type %s is invalid, must be a port type") % setype)

		( k, proto_d, low, high ) = self.__genkey(port, proto)

		(rc, exists) = semanage_port_exists(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not check if port %s/%s is defined") % (proto, port))
		if not exists:
			raise ValueError(_("Port %s/%s is not defined") % (proto,port))
	
		(rc, p) = semanage_port_query(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not query port %s/%s") % (proto, port))

		con = semanage_port_get_con(p)
			
		if (is_mls_enabled == 1) and (serange != ""):
			semanage_context_set_mls(self.sh, con, untranslate(serange))
		if setype != "":
			semanage_context_set_type(self.sh, con, setype)

		rc = semanage_port_modify_local(self.sh, k, p)
		if rc < 0:
			raise ValueError(_("Could not modify port %s/%s") % (proto, port))

		semanage_port_key_free(k)
		semanage_port_free(p)

	def modify(self, port, proto, serange, setype):
                self.begin()
                self.__modify(port, proto, serange, setype)
                self.commit()

	def deleteall(self):
		(rc, plist) = semanage_port_list_local(self.sh)
		if rc < 0:
			raise ValueError(_("Could not list the ports"))

                self.begin()

		for port in plist:
                       proto = semanage_port_get_proto(port)
                       proto_str = semanage_port_get_proto_str(proto)
                       low = semanage_port_get_low(port)
                       high = semanage_port_get_high(port)
                       port_str = "%s-%s" % (low, high)
                       ( k, proto_d, low, high ) = self.__genkey(port_str , proto_str)
                       if rc < 0:
                              raise ValueError(_("Could not create a key for %s") % port_str)

                       rc = semanage_port_del_local(self.sh, k)
                       if rc < 0:
                              raise ValueError(_("Could not delete the port %s") % port_str)
                       semanage_port_key_free(k)
	
                self.commit()

	def __delete(self, port, proto):
		( k, proto_d, low, high ) = self.__genkey(port, proto)
		(rc, exists) = semanage_port_exists(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not check if port %s/%s is defined") % (proto, port))
		if not exists:
			raise ValueError(_("Port %s/%s is not defined") % (proto, port))
		
		(rc, exists) = semanage_port_exists_local(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not check if port %s/%s is defined") % (proto, port))
		if not exists:
			raise ValueError(_("Port %s/%s is defined in policy, cannot be deleted") % (proto, port))

		rc = semanage_port_del_local(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not delete port %s/%s") % (proto, port))

		semanage_port_key_free(k)

	def delete(self, port, proto):
                self.begin()
                self.__delete(port, proto)
                self.commit()

	def get_all(self, locallist = 0):
		ddict = {}
                if locallist:
                       (rc, self.plist) = semanage_port_list_local(self.sh)
                else:
                       (rc, self.plist) = semanage_port_list(self.sh)
		if rc < 0:
			raise ValueError(_("Could not list ports"))

		for port in self.plist:
			con = semanage_port_get_con(port)
			ctype = semanage_context_get_type(con)
			if ctype == "reserved_port_t":
				continue
			level = semanage_context_get_mls(con)
			proto = semanage_port_get_proto(port)
			proto_str = semanage_port_get_proto_str(proto)
			low = semanage_port_get_low(port)
			high = semanage_port_get_high(port)
			ddict[(low, high, proto_str)] = (ctype, level)
		return ddict

	def get_all_by_type(self, locallist = 0):
		ddict = {}
                if locallist:
                       (rc, self.plist) = semanage_port_list_local(self.sh)
                else:
                       (rc, self.plist) = semanage_port_list(self.sh)
		if rc < 0:
			raise ValueError(_("Could not list ports"))

		for port in self.plist:
			con = semanage_port_get_con(port)
			ctype = semanage_context_get_type(con)
			if ctype == "reserved_port_t":
				continue
			proto = semanage_port_get_proto(port)
			proto_str = semanage_port_get_proto_str(proto)
			low = semanage_port_get_low(port)
			high = semanage_port_get_high(port)
			if (ctype, proto_str) not in ddict.keys():
				ddict[(ctype,proto_str)] = []
			if low == high:
				ddict[(ctype,proto_str)].append("%d" % low)
			else:
				ddict[(ctype,proto_str)].append("%d-%d" % (low, high))
		return ddict

        def customized(self):
                l = []
		ddict = self.get_all(True)
		keys = ddict.keys()
		keys.sort()
                for k in keys:
                       if k[0] == k[1]:
                              l.append("-a -t %s -p %s %s" % (ddict[k][0], k[2], k[0]))
                       else:
                              l.append("-a -t %s -p %s %s-%s" % (ddict[k][0], k[2], k[0], k[1]))
                return l

	def list(self, heading = 1, locallist = 0):
		ddict = self.get_all_by_type(locallist)
		keys = ddict.keys()
		if len(keys) == 0:
			return 
		keys.sort()

		if heading:
			print "%-30s %-8s %s\n" % (_("SELinux Port Type"), _("Proto"), _("Port Number"))
		for i in keys:
			rec = "%-30s %-8s " % i
			rec += "%s" % ddict[i][0]
			for p in ddict[i][1:]:
				rec += ", %s" % p
			print rec

class nodeRecords(semanageRecords):
       try:
	       valid_types =  sepolicy.info(sepolicy.ATTRIBUTE,"node_type")[0]["types"]
       except RuntimeError:
	       valid_types = []

       def __init__(self, store = ""):
               semanageRecords.__init__(self,store)
               self.protocol = ["ipv4", "ipv6"]

       def validate(self, addr, mask, protocol):
               newaddr=addr
               newmask=mask
               newprotocol=""

               if addr == "":
                       raise ValueError(_("Node Address is required"))

               # verify valid comination
               if len(mask) == 0 or mask[0] == "/":
                       i = IP(addr + mask)
                       newaddr = i.strNormal(0)
                       newmask = str(i.netmask())
                       if newmask == "0.0.0.0" and i.version() == 6:
                               newmask = "::"

                       protocol = "ipv%d" % i.version()

               try:
                      newprotocol = self.protocol.index(protocol)
               except:
                      raise ValueError(_("Unknown or missing protocol"))

               return newaddr, newmask, newprotocol

       def __add(self, addr, mask, proto, serange, ctype):
               addr, mask, proto = self.validate(addr, mask, proto)

               if is_mls_enabled == 1:
                       if serange == "":
                               serange = "s0"
                       else:
                               serange = untranslate(serange)

               if ctype == "":
                       raise ValueError(_("SELinux node type is required"))

	       if ctype not in self.valid_types:
		       raise ValueError(_("Type %s is invalid, must be a node type") % ctype)

               (rc, k) = semanage_node_key_create(self.sh, addr, mask, proto)
               if rc < 0:
                       raise ValueError(_("Could not create key for %s") % addr)
               if rc < 0:
                       raise ValueError(_("Could not check if addr %s is defined") % addr)

               (rc, exists) = semanage_node_exists(self.sh, k)
               if exists:
                       raise ValueError(_("Addr %s already defined") % addr)

               (rc, node) = semanage_node_create(self.sh)
               if rc < 0:
                       raise ValueError(_("Could not create addr for %s") % addr)
               semanage_node_set_proto(node, proto)

               rc = semanage_node_set_addr(self.sh, node, proto, addr)
               (rc, con) = semanage_context_create(self.sh)
               if rc < 0:
                       raise ValueError(_("Could not create context for %s") % addr)

               rc = semanage_node_set_mask(self.sh, node, proto, mask)
               if rc < 0:
                       raise ValueError(_("Could not set mask for %s") % addr)

               rc = semanage_context_set_user(self.sh, con, "system_u")
               if rc < 0:
                       raise ValueError(_("Could not set user in addr context for %s") % addr)

               rc = semanage_context_set_role(self.sh, con, "object_r")
               if rc < 0:
                       raise ValueError(_("Could not set role in addr context for %s") % addr)

               rc = semanage_context_set_type(self.sh, con, ctype)
               if rc < 0:
                       raise ValueError(_("Could not set type in addr context for %s") % addr)

               if (is_mls_enabled == 1) and (serange != ""):
                       rc = semanage_context_set_mls(self.sh, con, serange)
                       if rc < 0:
                               raise ValueError(_("Could not set mls fields in addr context for %s") % addr)

               rc = semanage_node_set_con(self.sh, node, con)
               if rc < 0:
                       raise ValueError(_("Could not set addr context for %s") % addr)

               rc = semanage_node_modify_local(self.sh, k, node)
               if rc < 0:
                       raise ValueError(_("Could not add addr %s") % addr)

               semanage_context_free(con)
               semanage_node_key_free(k)
               semanage_node_free(node)

       def add(self, addr, mask, proto, serange, ctype):
                self.begin()
                self.__add(addr, mask, proto, serange, ctype)
                self.commit()

       def __modify(self, addr, mask, proto, serange, setype):
               addr, mask, proto = self.validate(addr, mask, proto)

               if serange == "" and setype == "":
                       raise ValueError(_("Requires setype or serange"))

	       if setype and setype not in self.valid_types:
		       raise ValueError(_("Type %s is invalid, must be a node type") % setype)

               (rc, k) = semanage_node_key_create(self.sh, addr, mask, proto)
               if rc < 0:
                       raise ValueError(_("Could not create key for %s") % addr)

               (rc, exists) = semanage_node_exists(self.sh, k)
               if rc < 0:
                       raise ValueError(_("Could not check if addr %s is defined") % addr)
               if not exists:
                       raise ValueError(_("Addr %s is not defined") % addr)

               (rc, node) = semanage_node_query(self.sh, k)
               if rc < 0:
                       raise ValueError(_("Could not query addr %s") % addr)

               con = semanage_node_get_con(node)
               if (is_mls_enabled == 1) and (serange != ""):
                       semanage_context_set_mls(self.sh, con, untranslate(serange))
               if setype != "":
                       semanage_context_set_type(self.sh, con, setype)

               rc = semanage_node_modify_local(self.sh, k, node)
               if rc < 0:
                       raise ValueError(_("Could not modify addr %s") % addr)

               semanage_node_key_free(k)
               semanage_node_free(node)

       def modify(self, addr, mask, proto, serange, setype):
                self.begin()
                self.__modify(addr, mask, proto, serange, setype)
                self.commit()

       def __delete(self, addr, mask, proto):

               addr, mask, proto = self.validate(addr, mask, proto)

               (rc, k) = semanage_node_key_create(self.sh, addr, mask, proto)
               if rc < 0:
                       raise ValueError(_("Could not create key for %s") % addr)

               (rc, exists) = semanage_node_exists(self.sh, k)
               if rc < 0:
                       raise ValueError(_("Could not check if addr %s is defined") % addr)
               if not exists:
                       raise ValueError(_("Addr %s is not defined") % addr)

               (rc, exists) = semanage_node_exists_local(self.sh, k)
               if rc < 0:
                       raise ValueError(_("Could not check if addr %s is defined") % addr)
               if not exists:
                       raise ValueError(_("Addr %s is defined in policy, cannot be deleted") % addr)

               rc = semanage_node_del_local(self.sh, k)
               if rc < 0:
                       raise ValueError(_("Could not delete addr %s") % addr)

               semanage_node_key_free(k)

       def delete(self, addr, mask, proto):
              self.begin()
              self.__delete(addr, mask, proto)
              self.commit()
		
       def deleteall(self):
              (rc, nlist) = semanage_node_list_local(self.sh)
              if rc < 0:
                     raise ValueError(_("Could not deleteall node mappings"))

              self.begin()
              for node in nlist:
                     self.__delete(semanage_node_get_addr(self.sh, node)[1], semanage_node_get_mask(self.sh, node)[1], self.protocol[semanage_node_get_proto(node)])
              self.commit()

       def get_all(self, locallist = 0):
               ddict = {}
	       if locallist :
			(rc, self.ilist) = semanage_node_list_local(self.sh)
	       else:
	                (rc, self.ilist) = semanage_node_list(self.sh)
               if rc < 0:
                       raise ValueError(_("Could not list addrs"))

               for node in self.ilist:
                       con = semanage_node_get_con(node)
                       addr = semanage_node_get_addr(self.sh, node)
                       mask = semanage_node_get_mask(self.sh, node)
                       proto = self.protocol[semanage_node_get_proto(node)]
                       ddict[(addr[1], mask[1], proto)] = (semanage_context_get_user(con), semanage_context_get_role(con), semanage_context_get_type(con), semanage_context_get_mls(con))

               return ddict

       def customized(self):
               l = []
               ddict = self.get_all(True)
               keys = ddict.keys()
               keys.sort()
               for k in keys:
                      l.append("-a -M %s -p %s -t %s %s" % (k[1], k[2],ddict[k][2], k[0]))
               return l

       def list(self, heading = 1, locallist = 0):
               ddict = self.get_all(locallist)
               keys = ddict.keys()
	       if len(keys) == 0:
		       return 
               keys.sort()

               if heading:
                       print "%-18s %-18s %-5s %-5s\n" % ("IP Address", "Netmask", "Protocol", "Context")
               if is_mls_enabled:
			for k in keys:
				val = ''
				for fields in k:
					val = val + '\t' + str(fields)
                                print "%-18s %-18s %-5s %s:%s:%s:%s " % (k[0],k[1],k[2],ddict[k][0], ddict[k][1],ddict[k][2], translate(ddict[k][3], False))
               else:
                       for k in keys:
                               print "%-18s %-18s %-5s %s:%s:%s " % (k[0],k[1],k[2],ddict[k][0], ddict[k][1],ddict[k][2])


class interfaceRecords(semanageRecords):
	def __init__(self, store = ""):
		semanageRecords.__init__(self, store)

	def __add(self, interface, serange, ctype):
		if is_mls_enabled == 1:
			if serange == "":
				serange = "s0"
			else:
				serange = untranslate(serange)
			
		if ctype == "":
			raise ValueError(_("SELinux Type is required"))

		(rc, k) = semanage_iface_key_create(self.sh, interface)
		if rc < 0:
			raise ValueError(_("Could not create key for %s") % interface)

		(rc, exists) = semanage_iface_exists(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not check if interface %s is defined") % interface)
		if exists:
			raise ValueError(_("Interface %s already defined") % interface)

		(rc, iface) = semanage_iface_create(self.sh)
		if rc < 0:
			raise ValueError(_("Could not create interface for %s") % interface)
		
		rc = semanage_iface_set_name(self.sh, iface, interface)
		(rc, con) = semanage_context_create(self.sh)
		if rc < 0:
			raise ValueError(_("Could not create context for %s") % interface)

		rc = semanage_context_set_user(self.sh, con, "system_u")
		if rc < 0:
			raise ValueError(_("Could not set user in interface context for %s") % interface)

		rc = semanage_context_set_role(self.sh, con, "object_r")
		if rc < 0:
			raise ValueError(_("Could not set role in interface context for %s") % interface)

		rc = semanage_context_set_type(self.sh, con, ctype)
		if rc < 0:
			raise ValueError(_("Could not set type in interface context for %s") % interface)

		if (is_mls_enabled == 1) and (serange != ""):
			rc = semanage_context_set_mls(self.sh, con, serange)
			if rc < 0:
				raise ValueError(_("Could not set mls fields in interface context for %s") % interface)

		rc = semanage_iface_set_ifcon(self.sh, iface, con)
		if rc < 0:
			raise ValueError(_("Could not set interface context for %s") % interface)

		rc = semanage_iface_set_msgcon(self.sh, iface, con)
		if rc < 0:
			raise ValueError(_("Could not set message context for %s") % interface)

		rc = semanage_iface_modify_local(self.sh, k, iface)
		if rc < 0:
			raise ValueError(_("Could not add interface %s") % interface)

		semanage_context_free(con)
		semanage_iface_key_free(k)
		semanage_iface_free(iface)

	def add(self, interface, serange, ctype):
                self.begin()
                self.__add(interface, serange, ctype)
                self.commit()

	def __modify(self, interface, serange, setype):
		if serange == "" and setype == "":
			raise ValueError(_("Requires setype or serange"))

		(rc, k) = semanage_iface_key_create(self.sh, interface)
		if rc < 0:
			raise ValueError(_("Could not create key for %s") % interface)

		(rc, exists) = semanage_iface_exists(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not check if interface %s is defined") % interface)
		if not exists:
			raise ValueError(_("Interface %s is not defined") % interface)
	
		(rc, iface) = semanage_iface_query(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not query interface %s") % interface)

		con = semanage_iface_get_ifcon(iface)
			
		if (is_mls_enabled == 1) and (serange != ""):
			semanage_context_set_mls(self.sh, con, untranslate(serange))
		if setype != "":
			semanage_context_set_type(self.sh, con, setype)

		rc = semanage_iface_modify_local(self.sh, k, iface)
		if rc < 0:
			raise ValueError(_("Could not modify interface %s") % interface)
		
		semanage_iface_key_free(k)
		semanage_iface_free(iface)

	def modify(self, interface, serange, setype):
                self.begin()
                self.__modify(interface, serange, setype)
                self.commit()

	def __delete(self, interface):
		(rc, k) = semanage_iface_key_create(self.sh, interface)
		if rc < 0:
			raise ValueError(_("Could not create key for %s") % interface)

		(rc, exists) = semanage_iface_exists(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not check if interface %s is defined") % interface)
		if not exists:
			raise ValueError(_("Interface %s is not defined") % interface)

		(rc, exists) = semanage_iface_exists_local(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not check if interface %s is defined") % interface)
		if not exists:
			raise ValueError(_("Interface %s is defined in policy, cannot be deleted") % interface)

		rc = semanage_iface_del_local(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not delete interface %s") % interface)

		semanage_iface_key_free(k)

	def delete(self, interface):
                self.begin()
                self.__delete(interface)
                self.commit()
		
        def deleteall(self):
		(rc, ulist) = semanage_iface_list_local(self.sh)
		if rc < 0:
			raise ValueError(_("Could not delete all interface  mappings"))

                self.begin()
		for i in ulist:
			self.__delete(semanage_iface_get_name(i))
                self.commit()

	def get_all(self, locallist = 0):
		ddict = {}
                if locallist:
                       (rc, self.ilist) = semanage_iface_list_local(self.sh)
                else:
                       (rc, self.ilist) = semanage_iface_list(self.sh)
		if rc < 0:
			raise ValueError(_("Could not list interfaces"))

		for interface in self.ilist:
			con = semanage_iface_get_ifcon(interface)
			ddict[semanage_iface_get_name(interface)] = (semanage_context_get_user(con), semanage_context_get_role(con), semanage_context_get_type(con), semanage_context_get_mls(con))

		return ddict
			
        def customized(self):
                l = []
                ddict = self.get_all(True)
                keys = ddict.keys()
                keys.sort()
                for k in keys:
                       l.append("-a -t %s %s" % (ddict[k][2], k))
                return l

	def list(self, heading = 1, locallist = 0):
		ddict = self.get_all(locallist)
		keys = ddict.keys()
		if len(keys) == 0:
			return 
		keys.sort()

		if heading:
			print "%-30s %s\n" % (_("SELinux Interface"), _("Context"))
		if is_mls_enabled:
			for k in keys:
				print "%-30s %s:%s:%s:%s " % (k,ddict[k][0], ddict[k][1],ddict[k][2], translate(ddict[k][3], False))
		else:
			for k in keys:
				print "%-30s %s:%s:%s " % (k,ddict[k][0], ddict[k][1],ddict[k][2])
			
class fcontextRecords(semanageRecords):
	try:
		valid_types =  sepolicy.info(sepolicy.ATTRIBUTE,"file_type")[0]["types"]
		valid_types +=  sepolicy.info(sepolicy.ATTRIBUTE,"device_node")[0]["types"]
                valid_types.append("<<none>>")
	except RuntimeError:
		valid_types = []

	def __init__(self, store = ""):
		semanageRecords.__init__(self, store)
                self.equiv = {}
                self.equiv_dist = {}
                self.equal_ind = False
                try:
                       fd = open(selinux.selinux_file_context_subs_path(), "r")
                       for i in fd.readlines():
                              i = i.strip()
                              if len(i) == 0:
                                     continue
                              if i.startswith("#"):
                                     continue
                              target, substitute = i.split()
                              self.equiv[target] = substitute
                       fd.close()
                except IOError:
                       pass
                try:
                       fd = open(selinux.selinux_file_context_subs_dist_path(), "r")
                       for i in fd.readlines():
                              i = i.strip()
                              if len(i) == 0:
                                     continue
                              if i.startswith("#"):
                                     continue
                              target, substitute = i.split()
                              self.equiv_dist[target] = substitute
                       fd.close()
                except IOError:
                       pass

        def commit(self):
                if self.equal_ind:
                       subs_file = selinux.selinux_file_context_subs_path()
                       tmpfile = "%s.tmp" % subs_file
                       fd = open(tmpfile, "w")
                       for target in self.equiv.keys():
                              fd.write("%s %s\n" % (target, self.equiv[target]))
                       fd.close()
                       try:
                              os.chmod(tmpfile, os.stat(subs_file)[stat.ST_MODE])
                       except:
                              pass
                       os.rename(tmpfile,subs_file)
                       self.equal_ind = False
		semanageRecords.commit(self)

        def add_equal(self, target, substitute):
                self.begin()
                if target != "/" and target[-1] == "/":
                        raise ValueError(_("Target %s is not valid. Target is not allowed to end with '/'") % target )

                if substitute != "/" and substitute[-1] == "/":
                       raise ValueError(_("Substiture %s is not valid. Substitute is not allowed to end with '/'") % substitute )

                if target in self.equiv.keys():
                       raise ValueError(_("Equivalence class for %s already exists") % target)
                self.validate(target)

		for fdict in (self.equiv, self.equiv_dist):
			for i in fdict:
				if i.startswith(target + "/"):
					raise ValueError(_("File spec %s conflicts with equivalency rule '%s %s'") % (target, i, fdict[i]))

                self.equiv[target] = substitute
                self.equal_ind = True
                self.commit()

        def modify_equal(self, target, substitute):
                self.begin()
                if target not in self.equiv.keys():
                       raise ValueError(_("Equivalence class for %s does not exists") % target)
                self.equiv[target] = substitute
                self.equal_ind = True
                self.commit()

        def createcon(self, target, seuser = "system_u"):
                (rc, con) = semanage_context_create(self.sh)
                if rc < 0:
                       raise ValueError(_("Could not create context for %s") % target)
		if seuser == "":
			seuser = "system_u"

                rc = semanage_context_set_user(self.sh, con, seuser)
                if rc < 0:
                       raise ValueError(_("Could not set user in file context for %s") % target)
		
                rc = semanage_context_set_role(self.sh, con, "object_r")
                if rc < 0:
                       raise ValueError(_("Could not set role in file context for %s") % target)

		if is_mls_enabled == 1:
                       rc = semanage_context_set_mls(self.sh, con, "s0")
                       if rc < 0:
                              raise ValueError(_("Could not set mls fields in file context for %s") % target)

                return con

        def validate(self, target):
               if target == "" or target.find("\n") >= 0:
                      raise ValueError(_("Invalid file specification"))
               if target.find(" ") != -1:
                      raise ValueError(_("File specification can not include spaces"))
	       for fdict in (self.equiv, self.equiv_dist):
		       for i in fdict:
			       if target.startswith(i+"/"):
				       t = re.sub(i, fdict[i], target)
				       raise ValueError(_("File spec %s conflicts with equivalency rule '%s %s'; Try adding '%s' instead") % (target, i, fdict[i], t))


	def __add(self, target, type, ftype = "", serange = "", seuser = "system_u"):
                self.validate(target)

		if is_mls_enabled == 1:
                       serange = untranslate(serange)
			
		if type == "":
			raise ValueError(_("SELinux Type is required"))

		if type not in self.valid_types:
			raise ValueError(_("Type %s is invalid, must be a file or device type") % type)

		(rc, k) = semanage_fcontext_key_create(self.sh, target, file_types[ftype])
		if rc < 0:
			raise ValueError(_("Could not create key for %s") % target)

		(rc, exists) = semanage_fcontext_exists(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not check if file context for %s is defined") % target)

		if not exists:
                       (rc, exists) = semanage_fcontext_exists_local(self.sh, k)
                       if rc < 0:
                              raise ValueError(_("Could not check if file context for %s is defined") % target)

                if exists:
                       raise ValueError(_("File context for %s already defined") % target)

		(rc, fcontext) = semanage_fcontext_create(self.sh)
		if rc < 0:
			raise ValueError(_("Could not create file context for %s") % target)
		
		rc = semanage_fcontext_set_expr(self.sh, fcontext, target)
                if type != "<<none>>":
                       con = self.createcon(target, seuser)

                       rc = semanage_context_set_type(self.sh, con, type)
                       if rc < 0:
                              raise ValueError(_("Could not set type in file context for %s") % target)

                       if (is_mls_enabled == 1) and (serange != ""):
                              rc = semanage_context_set_mls(self.sh, con, serange)
                              if rc < 0:
                                     raise ValueError(_("Could not set mls fields in file context for %s") % target)
                       rc = semanage_fcontext_set_con(self.sh, fcontext, con)
                       if rc < 0:
                              raise ValueError(_("Could not set file context for %s") % target)

		semanage_fcontext_set_type(fcontext, file_types[ftype])

		rc = semanage_fcontext_modify_local(self.sh, k, fcontext)
		if rc < 0:
			raise ValueError(_("Could not add file context for %s") % target)

                if type != "<<none>>":
                       semanage_context_free(con)
		semanage_fcontext_key_free(k)
		semanage_fcontext_free(fcontext)

	def add(self, target, type, ftype = "", serange = "", seuser = "system_u"):
                self.begin()
                self.__add(target, type, ftype, serange, seuser)
                self.commit()

	def __modify(self, target, setype, ftype, serange, seuser):
		if serange == "" and setype == "" and seuser == "":
			raise ValueError(_("Requires setype, serange or seuser"))
		if setype and setype not in self.valid_types:
			raise ValueError(_("Type %s is invalid, must be a port type") % setype)

                self.validate(target)

		(rc, k) = semanage_fcontext_key_create(self.sh, target, file_types[ftype])
		if rc < 0:
			raise ValueError(_("Could not create a key for %s") % target)

		(rc, exists) = semanage_fcontext_exists(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not check if file context for %s is defined") % target)
		if not exists:
                       (rc, exists) = semanage_fcontext_exists_local(self.sh, k)
                       if not exists:
                              raise ValueError(_("File context for %s is not defined") % target)
		
		(rc, fcontext) = semanage_fcontext_query_local(self.sh, k)
		if rc < 0:
                       (rc, fcontext) = semanage_fcontext_query(self.sh, k)
                       if rc < 0:
                              raise ValueError(_("Could not query file context for %s") % target)

                if setype != "<<none>>":
                       con = semanage_fcontext_get_con(fcontext)
			
                       if con == None:
                              con = self.createcon(target)
                              
                       if (is_mls_enabled == 1) and (serange != ""):
                              semanage_context_set_mls(self.sh, con, untranslate(serange))
                       if seuser != "":
                              semanage_context_set_user(self.sh, con, seuser)
                              
                       if setype != "":
                              semanage_context_set_type(self.sh, con, setype)

                       rc = semanage_fcontext_set_con(self.sh, fcontext, con)
                       if rc < 0:
                              raise ValueError(_("Could not set file context for %s") % target)
                else:
                       rc = semanage_fcontext_set_con(self.sh, fcontext, None)
                       if rc < 0:
                              raise ValueError(_("Could not set file context for %s") % target)
                       
		rc = semanage_fcontext_modify_local(self.sh, k, fcontext)
		if rc < 0:
			raise ValueError(_("Could not modify file context for %s") % target)

		semanage_fcontext_key_free(k)
		semanage_fcontext_free(fcontext)

	def modify(self, target, setype, ftype, serange, seuser):
                self.begin()
                self.__modify(target, setype, ftype, serange, seuser)
                self.commit()

	def deleteall(self):
		(rc, flist) = semanage_fcontext_list_local(self.sh)
		if rc < 0:
			raise ValueError(_("Could not list the file contexts"))

                self.begin()

		for fcontext in flist:
                       target = semanage_fcontext_get_expr(fcontext)
                       ftype = semanage_fcontext_get_type(fcontext)
                       ftype_str = semanage_fcontext_get_type_str(ftype)
                       (rc, k) = semanage_fcontext_key_create(self.sh, target, file_types[ftype_str])
                       if rc < 0:
                              raise ValueError(_("Could not create a key for %s") % target)

                       rc = semanage_fcontext_del_local(self.sh, k)
                       if rc < 0:
                              raise ValueError(_("Could not delete the file context %s") % target)
                       semanage_fcontext_key_free(k)
	
                self.equiv = {}
                self.equal_ind = True
                self.commit()

	def __delete(self, target, ftype):
                if target in self.equiv.keys():
                       self.equiv.pop(target)
                       self.equal_ind = True
                       return

		(rc,k) = semanage_fcontext_key_create(self.sh, target, file_types[ftype])
		if rc < 0:
			raise ValueError(_("Could not create a key for %s") % target)

		(rc, exists) = semanage_fcontext_exists_local(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not check if file context for %s is defined") % target)
		if not exists:
			(rc, exists) = semanage_fcontext_exists(self.sh, k)
			if rc < 0:
				raise ValueError(_("Could not check if file context for %s is defined") % target)
			if exists:
				raise ValueError(_("File context for %s is defined in policy, cannot be deleted") % target)
			else:
				raise ValueError(_("File context for %s is not defined") % target)

		rc = semanage_fcontext_del_local(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not delete file context for %s") % target)

		semanage_fcontext_key_free(k)		

	def delete(self, target, ftype):
                self.begin()
                self.__delete( target, ftype)
                self.commit()

	def get_all(self, locallist = 0):
                if locallist:
                       (rc, self.flist) = semanage_fcontext_list_local(self.sh)
                else:
                       (rc, self.flist) = semanage_fcontext_list(self.sh)
                       if rc < 0:
                              raise ValueError(_("Could not list file contexts"))

                       (rc, fclocal) = semanage_fcontext_list_local(self.sh)
                       if rc < 0:
                              raise ValueError(_("Could not list local file contexts"))

                       self.flist += fclocal

                ddict = {}
		for fcontext in self.flist:
			expr = semanage_fcontext_get_expr(fcontext)
			ftype = semanage_fcontext_get_type(fcontext)
			ftype_str = semanage_fcontext_get_type_str(ftype)
			con = semanage_fcontext_get_con(fcontext)
			if con:
                               ddict[(expr, ftype_str)] = (semanage_context_get_user(con), semanage_context_get_role(con), semanage_context_get_type(con), semanage_context_get_mls(con))
			else:
				ddict[(expr, ftype_str)] = con

		return ddict
			
        def customized(self):
               l = []
               fcon_dict = self.get_all(True)
               keys = fcon_dict.keys()
               keys.sort()
               for k in keys:
                      if fcon_dict[k]:
                             l.append("-a -f %s -t %s '%s'" % (file_type_str_to_option[k[1]], fcon_dict[k][2], k[0]))

	       if len(self.equiv):
                      for target in self.equiv.keys():
			     l.append("-a -e %s %s" % (self.equiv[target], target))
               return l

	def list(self, heading = 1, locallist = 0 ):
		fcon_dict = self.get_all(locallist)
                keys = fcon_dict.keys()
		if len(keys) != 0:
			keys.sort()
			if heading:
				print "%-50s %-18s %s\n" % (_("SELinux fcontext"), _("type"), _("Context"))
			for k in keys:
				if fcon_dict[k]:
					if is_mls_enabled:
						print "%-50s %-18s %s:%s:%s:%s " % (k[0], k[1], fcon_dict[k][0], fcon_dict[k][1], fcon_dict[k][2], translate(fcon_dict[k][3],False))
					else:
						print "%-50s %-18s %s:%s:%s " % (k[0], k[1], fcon_dict[k][0], fcon_dict[k][1],fcon_dict[k][2])
				else:
					print "%-50s %-18s <<None>>" % (k[0], k[1])

		if len(self.equiv_dist):
		       if not locallist:
			       if heading:
				       print _("\nSELinux Distribution fcontext Equivalence \n")
			       for target in self.equiv_dist.keys():
				       print "%s = %s" % (target, self.equiv_dist[target])
		if len(self.equiv):
                       if heading:
                              print _("\nSELinux Local fcontext Equivalence \n")

                       for target in self.equiv.keys():
                              print "%s = %s" % (target, self.equiv[target])
				
class booleanRecords(semanageRecords):
	def __init__(self, store = ""):
		semanageRecords.__init__(self, store)
                self.dict = {}
                self.dict["TRUE"] = 1
                self.dict["FALSE"] = 0
                self.dict["ON"] = 1
                self.dict["OFF"] = 0
                self.dict["1"] = 1
                self.dict["0"] = 0

		try:
			rc, self.current_booleans = selinux.security_get_boolean_names()
			rc, ptype = selinux.selinux_getpolicytype()
		except:
			self.current_booleans = []
			ptype = None

		if self.store == None or self.store == ptype:
			self.modify_local = True
		else:
			self.modify_local = False

	def __mod(self, name, value):
                name = selinux.selinux_boolean_sub(name)

                (rc, k) = semanage_bool_key_create(self.sh, name)
                if rc < 0:
                       raise ValueError(_("Could not create a key for %s") % name)
                (rc, exists) = semanage_bool_exists(self.sh, k)
                if rc < 0:
                       raise ValueError(_("Could not check if boolean %s is defined") % name)
                if not exists:
                       raise ValueError(_("Boolean %s is not defined") % name)	
                
                (rc, b) = semanage_bool_query(self.sh, k)
                if rc < 0:
                       raise ValueError(_("Could not query file context %s") % name)

                if value.upper() in self.dict:
                       semanage_bool_set_value(b, self.dict[value.upper()])
                else:
                       raise ValueError(_("You must specify one of the following values: %s") % ", ".join(self.dict.keys()) )
                
		if self.modify_local and name in self.current_booleans:
			rc = semanage_bool_set_active(self.sh, k, b)
			if rc < 0:
				raise ValueError(_("Could not set active value of boolean %s") % name)
                rc = semanage_bool_modify_local(self.sh, k, b)
                if rc < 0:
                       raise ValueError(_("Could not modify boolean %s") % name)
		semanage_bool_key_free(k)
		semanage_bool_free(b)

	def modify(self, name, value = None, use_file = False):
                self.begin()
                if use_file:
                       fd = open(name)
                       for b in fd.read().split("\n"):
                              b = b.strip()
                              if len(b) == 0:
                                     continue

                              try:
                                     boolname, val = b.split("=")
                              except ValueError:
                                     raise ValueError(_("Bad format %s: Record %s" % ( name, b) ))
                              self.__mod(boolname.strip(), val.strip())
                       fd.close()
                else:
                       self.__mod(name, value)

                self.commit()
		
	def __delete(self, name):
                name = selinux.selinux_boolean_sub(name)

                (rc, k) = semanage_bool_key_create(self.sh, name)
                if rc < 0:
                      raise ValueError(_("Could not create a key for %s") % name)
		(rc, exists) = semanage_bool_exists(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not check if boolean %s is defined") % name)
		if not exists:
			raise ValueError(_("Boolean %s is not defined") % name)
	
		(rc, exists) = semanage_bool_exists_local(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not check if boolean %s is defined") % name)
		if not exists:
			raise ValueError(_("Boolean %s is defined in policy, cannot be deleted") % name)

		rc = semanage_bool_del_local(self.sh, k)
		if rc < 0:
			raise ValueError(_("Could not delete boolean %s") % name)
	
		semanage_bool_key_free(k)

	def delete(self, name):
                self.begin()
                self.__delete(name)
                self.commit()

	def deleteall(self):
		(rc, self.blist) = semanage_bool_list_local(self.sh)
		if rc < 0:
			raise ValueError(_("Could not list booleans"))

                self.begin()

		for boolean in self.blist:
                       name = semanage_bool_get_name(boolean)
                       self.__delete(name)

                self.commit()
	
	def get_all(self, locallist = 0):
		ddict = {}
                if locallist:
                       (rc, self.blist) = semanage_bool_list_local(self.sh)
                else:
                       (rc, self.blist) = semanage_bool_list(self.sh)
		if rc < 0:
			raise ValueError(_("Could not list booleans"))

		for boolean in self.blist:
                       value = []
                       name = semanage_bool_get_name(boolean)
                       value.append(semanage_bool_get_value(boolean))
		       if self.modify_local and boolean in self.current_booleans:
			       value.append(selinux.security_get_boolean_pending(name))
			       value.append(selinux.security_get_boolean_active(name))
		       else:
			       value.append(value[0])
			       value.append(value[0])
                       ddict[name] = value

		return ddict
			
        def get_desc(self, name):
		name = selinux.selinux_boolean_sub(name)
		return boolean_desc(name)

        def get_category(self, name):
		name = selinux.selinux_boolean_sub(name)
		return boolean_category(name)

        def customized(self):
               l = []
               ddict = self.get_all(True)
               keys = ddict.keys()
               keys.sort()
               for k in keys:
                      if ddict[k]:
                             l.append("-m -%s %s" %  (ddict[k][2], k))
               return l

	def list(self, heading = True, locallist = False, use_file = False):
                on_off = (_("off"), _("on")) 
		if use_file:
                       ddict = self.get_all(locallist)
                       keys = ddict.keys()
                       for k in keys:
                              if ddict[k]:
                                     print "%s=%s" %  (k, ddict[k][2])
                       return
		ddict = self.get_all(locallist)
		keys = ddict.keys()
		if len(keys) == 0:
			return 

		if heading:
			print "%-30s %s  %s %s\n" % (_("SELinux boolean"),_("State"), _("Default"), _("Description"))
		for k in keys:
			if ddict[k]:
				print "%-30s (%-5s,%5s)  %s" %  (k, on_off[selinux.security_get_boolean_active(k)], on_off[ddict[k][2]], self.get_desc(k))
