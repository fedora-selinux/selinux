all:
	LDFLAGS="" python setup.py build

install: all
	LDFLAGS="" python setup.py install --root=$(DESTDIR)/

clean:
	rm -rf build *~
