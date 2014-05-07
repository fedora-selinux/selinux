# Installation directories.
PREFIX ?= $(DESTDIR)/usr
LIBDIR ?= $(PREFIX)/lib
SBINDIR ?= $(PREFIX)/sbin
MANDIR = $(PREFIX)/share/man
PYTHON ?= /usr/bin/python
BASHCOMPLETIONDIR ?= $(DESTDIR)/usr/share/bash-completion/completions

TARGETS=semanage

BASHCOMPLETIONS=semanage-bash-completion.sh 

all: $(TARGETS)

install: all
	[ -d $(MANDIR)/man8 ] || mkdir -p $(MANDIR)/man8
	-mkdir -p $(SBINDIR)
	install -m 755 semanage $(SBINDIR)
	install -m 644 *.8 $(MANDIR)/man8
	LDFLAGS="" ${PYTHON} setup.py install --root=$(DESTDIR)/
	-mkdir -p $(BASHCOMPLETIONDIR)
	install -m 644 $(BASHCOMPLETIONS) $(BASHCOMPLETIONDIR)/semanage

test:
	@python test-semanage.py -a
clean:

indent:

relabel:
