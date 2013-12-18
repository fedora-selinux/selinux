# Installation directories.
PREFIX ?= $(DESTDIR)/usr
GODIR ?= $(PREFIX)/share/gocode/src/selinux

all:

install: 
	[ -d $(GODIR) ] || mkdir -p $(GODIR)
	install -m 644 selinux.go $(GODIR)

test:

clean:

indent:

relabel:
