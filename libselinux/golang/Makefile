# Installation directories.
PREFIX ?= $(DESTDIR)/usr
LIBDIR ?= $(DESTDIR)/usr/lib
GODIR ?= $(LIBDIR)/golang/src/pkg/github.com/selinux
all:

install: 
	[ -d $(GODIR) ] || mkdir -p $(GODIR)
	install -m 644 selinux.go $(GODIR)

test:
	@mkdir selinux
	@cp selinux.go selinux
	GOPATH=$(pwd) go run test.go 
	@rm -rf selinux

clean:
	@rm -f *~
	@rm -rf selinux
indent:

relabel:
