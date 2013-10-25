#
# Makefile for the PO files (translation) catalog
#

TOP	 = ../..

# What is this package?
NLSPACKAGE	= policycoreutils
POTFILE		= $(NLSPACKAGE).pot
INSTALL		= /usr/bin/install -c -p
INSTALL_DATA	= $(INSTALL) -m 644
INSTALL_DIR	= /usr/bin/install -d

# destination directory
INSTALL_NLS_DIR = $(DESTDIR)/usr/share/locale

# PO catalog handling
MSGMERGE	= msgmerge
MSGMERGE_FLAGS	= -q
XGETTEXT	= xgettext --default-domain=$(NLSPACKAGE)
MSGFMT		= msgfmt

# What do we need to do
POFILES		= $(wildcard *.po)
MOFILES		= $(patsubst %.po,%.mo,$(POFILES))
POTFILES = \
	../run_init/open_init_pty.c \
	../run_init/run_init.c \
	../semodule_link/semodule_link.c \
	../audit2allow/audit2allow \
	../semanage/seobject/__init__.py \
	../setsebool/setsebool.c \
	../newrole/newrole.c \
	../load_policy/load_policy.c \
	../sestatus/sestatus.c \
	../semodule/semodule.c \
	../setfiles/setfiles.c \
	../semodule_package/semodule_package.c \
	../semodule_deps/semodule_deps.c \
	../semodule_expand/semodule_expand.c \
	../scripts/chcat \
	../scripts/fixfiles \
	../restorecond/stringslist.c \
	../restorecond/restorecond.h \
	../restorecond/utmpwatcher.h \
	../restorecond/stringslist.h \
	../restorecond/restorecond.c \
	../restorecond/utmpwatcher.c \
	../gui/booleansPage.py \
	../gui/fcontextPage.py \
	../gui/loginsPage.py \
	../gui/modulesPage.py \
	../gui/polgen.glade \
	../gui/polgengui.py \
	../gui/portsPage.py \
	../gui/semanagePage.py \
	../gui/statusPage.py \
	../gui/system-config-selinux.glade \
	../gui/system-config-selinux.py \
	../gui/usersPage.py \
	../secon/secon.c \
	booleans.py \
	../sepolicy/sepolicy/help/booleans_more_show.txt \
	../sepolicy/sepolicy/help/booleans_more.txt  \
	../sepolicy/sepolicy/help/booleans_toggled.txt  \
	../sepolicy/sepolicy/help/booleans.txt  \
	../sepolicy/sepolicy/help/file_equiv.txt  \
	../sepolicy/sepolicy/help/files_apps.txt  \
	../sepolicy/sepolicy/help/files_exec.txt  \
	../sepolicy/sepolicy/help/files_write.txt  \
	../sepolicy/sepolicy/help/lockdown_permissive.txt  \
	../sepolicy/sepolicy/help/lockdown_ptrace.txt  \
	../sepolicy/sepolicy/help/lockdown.txt  \
	../sepolicy/sepolicy/help/lockdown_unconfined.txt  \
	../sepolicy/sepolicy/help/login_default.txt  \
	../sepolicy/sepolicy/help/login.txt  \
	../sepolicy/sepolicy/help/ports_inbound.txt  \
	../sepolicy/sepolicy/help/ports_outbound.txt  \
	../sepolicy/sepolicy/help/start.txt  \
	../sepolicy/sepolicy/help/system_boot_mode.txt  \
	../sepolicy/sepolicy/help/system_current_mode.txt  \
	../sepolicy/sepolicy/help/system_export.txt  \
	../sepolicy/sepolicy/help/system_policy_type.txt  \
	../sepolicy/sepolicy/help/system_relabel.txt  \
	../sepolicy/sepolicy/help/system.txt  \
	../sepolicy/sepolicy/help/transition_file.txt  \
	../sepolicy/sepolicy/help/transition_from_boolean_1.txt  \
	../sepolicy/sepolicy/help/transition_from_boolean_2.txt  \
	../sepolicy/sepolicy/help/transition_from_boolean.txt  \
	../sepolicy/sepolicy/help/transition_from.txt  \
	../sepolicy/sepolicy/help/transition_to.txt  \
	../sepolicy/sepolicy/help/users.txt  \
	../sepolicy/info.c \
	../sepolicy/search.c \
	../sepolicy/sepolicy.py \
	../sepolicy/sepolicy/communicate.py \
	../sepolicy/sepolicy/__init__.py \
	../sepolicy/sepolicy/network.py \
	../sepolicy/sepolicy/generate.py \
	../sepolicy/sepolicy/sepolicy.glade \
	../sepolicy/sepolicy/gui.py \
	../sepolicy/sepolicy/manpage.py \
	../sepolicy/sepolicy/transition.py \
	../sepolicy/sepolicy/templates/executable.py \
	../sepolicy/sepolicy/templates/__init__.py \
	../sepolicy/sepolicy/templates/network.py \
	../sepolicy/sepolicy/templates/rw.py \
	../sepolicy/sepolicy/templates/script.py \
	../sepolicy/sepolicy/templates/semodule.py \
	../sepolicy/sepolicy/templates/tmp.py \
	../sepolicy/sepolicy/templates/user.py \
	../sepolicy/sepolicy/templates/var_lib.py \
	../sepolicy/sepolicy/templates/var_log.py \
	../sepolicy/sepolicy/templates/var_run.py \
	../sepolicy/sepolicy/templates/var_spool.py

#default:: clean

all::  $(MOFILES)

booleans.py:
	sepolicy booleans -a > booleans.py

$(POTFILE): $(POTFILES) booleans.py
	$(XGETTEXT) --keyword=_ --keyword=N_ $(POTFILES)
	@if cmp -s $(NLSPACKAGE).po $(POTFILE); then \
	    rm -f $(NLSPACKAGE).po; \
	else \
	    mv -f $(NLSPACKAGE).po $(POTFILE); \
	fi; \

update-po: Makefile $(POTFILE) refresh-po
	@rm -f booleans.py

refresh-po: Makefile
	for cat in $(POFILES); do \
		lang=`basename $$cat .po`; \
		if $(MSGMERGE) $(MSGMERGE_FLAGS) $$lang.po $(POTFILE) > $$lang.pot ; then \
			mv -f $$lang.pot $$lang.po ; \
			echo "$(MSGMERGE) of $$lang succeeded" ; \
		else \
			echo "$(MSGMERGE) of $$lang failed" ; \
			rm -f $$lang.pot ; \
		fi \
	done

clean:
	@rm -fv *mo *~ .depend
	@rm -rf tmp

install: $(MOFILES)
	@for n in $(MOFILES); do \
	    l=`basename $$n .mo`; \
	    $(INSTALL_DIR) $(INSTALL_NLS_DIR)/$$l/LC_MESSAGES; \
	    $(INSTALL_DATA) --verbose $$n $(INSTALL_NLS_DIR)/$$l/LC_MESSAGES/$(NLSPACKAGE).mo; \
	done

%.mo: %.po
	$(MSGFMT) -o $@ $<
report:
	@for cat in $(wildcard *.po); do \
                echo -n "$$cat: "; \
                msgfmt -v --statistics -o /dev/null $$cat; \
        done

.PHONY: missing depend

relabel:
