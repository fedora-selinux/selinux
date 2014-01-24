# Installation directories.
PREFIX ?= $(DESTDIR)/usr
LIBDIR ?= $(DESTDIR)/usr/lib
GODIR ?= $(LIBDIR)/golang/src/pkg/github.com/selinux
all:

install: 
	[ -d $(GODIR) ] || mkdir -p $(GODIR)
	install -m 644 selinux.go $(GODIR)

test:

clean:

indent:

relabel:
