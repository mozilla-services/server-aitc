APPNAME = server-aitc
DEPS = https://github.com/mozilla-services/server-syncstorage
VIRTUALENV = virtualenv
NOSE = bin/nosetests -s --with-xunit
TESTS = aitc/tests
PYTHON = bin/python
EZ = bin/easy_install
COVEROPTS = --cover-html --cover-html-dir=html --with-coverage --cover-package=keyexchange
COVERAGE = bin/coverage
PYLINT = bin/pylint
PKGS = aitc
EZOPTIONS = -U -i $(PYPI)
PYPI = http://pypi.python.org/simple
PYPI2RPM = bin/pypi2rpm.py --index=$(PYPI)
PYPIOPTIONS = -i $(PYPI)
BUILDAPP = bin/buildapp
BUILDRPMS = bin/buildrpms
PYPI = http://pypi.python.org/simple
PYPI2RPM = bin/pypi2rpm.py --index=$(PYPI)
PYPIOPTIONS = -i $(PYPI)
CHANNEL = dev
RPM_CHANNEL = dev
INSTALL = bin/pip install
INSTALLOPTIONS = -U -i $(PYPI)

ifdef PYPIEXTRAS
	PYPIOPTIONS += -e $(PYPIEXTRAS)
	INSTALLOPTIONS += -f $(PYPIEXTRAS)
endif

ifdef PYPISTRICT
	PYPIOPTIONS += -s
	ifdef PYPIEXTRAS
		HOST = `python -c "import urlparse; print urlparse.urlparse('$(PYPI)')[1] + ',' + urlparse.urlparse('$(PYPIEXTRAS)')[1]"`

	else
		HOST = `python -c "import urlparse; print urlparse.urlparse('$(PYPI)')[1]"`
	endif

endif

INSTALL += $(INSTALLOPTIONS)

.PHONY: all build test cover build_rpms mach update

all:	build

build:
	$(VIRTUALENV) --no-site-packages --distribute .
	$(INSTALL) MoPyTools
	$(INSTALL) nose
	$(INSTALL) coverage
	$(INSTALL) WebTest
	$(BUILDAPP) -c $(CHANNEL) $(PYPIOPTIONS) $(DEPS)

update:
	$(BUILDAPP) -c $(CHANNEL) $(PYPIOPTIONS) $(DEPS)

test:
	$(NOSE) $(TESTS)

cover:
	$(NOSE) --with-coverage --cover-html --cover-package=aitc $(TESTS)

build_rpms:
	$(BUILDRPMS) -c $(RPM_CHANNEL) $(PYPIOPTIONS) $(DEPS)
	# PyZMQ sdist bundles don't play nice with pypi2rpm.
	# We need to build from a checkout of the tag.
	wget -O /tmp/pyzmq-2.1.11.tar.gz https://github.com/zeromq/pyzmq/tarball/v2.1.11
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms /tmp/pyzmq-2.1.11.tar.gz
	rm -f /tmp/pyzmq-2.1.11.tar.gz
	# We need some extra patches to gevent_zeromq
	wget -O /tmp/master.zip https://github.com/tarekziade/gevent-zeromq/zipball/master --no-check-certificate
	bin/pypi2rpm.py /tmp/master.zip --dist-dir=$(CURDIR)/rpms
	rm -f /tmp/master.zip
	# The simplejson rpms conflict with a RHEL6 system package.
	# Do a custom build so that they can overwrite rather than conflict.
	rm -f $(CURDIR)/rpms/python26-simplejson-2.4.0-1.x86_64.rpm
	wget -O /tmp/simplejson-2.4.0.tar.gz http://pypi.python.org/packages/source/s/simplejson/simplejson-2.4.0.tar.gz
	cd /tmp; tar -xzvf simplejson-2.4.0.tar.gz
	cd /tmp/simplejson-2.4.0; python setup.py  --command-packages=pypi2rpm.command bdist_rpm2 --binary-only --name=python-simplejson --dist-dir=$(CURDIR)/rpms
	rm -rf /tmp/simplejson-2.4.0
	rm -f /tmp/simplejson-2.4.0.tar.gz

mock: build build_rpms
	mock init
	mock --install python26 python26-setuptools
	cd rpms; wget http://mrepo.mozilla.org/mrepo/5-x86_64/RPMS.mozilla-services/libmemcached-devel-0.50-1.x86_64.rpm
	cd rpms; wget http://mrepo.mozilla.org/mrepo/5-x86_64/RPMS.mozilla-services/libmemcached-0.50-1.x86_64.rpm
	cd rpms; wget http://mrepo.mozilla.org/mrepo/5-x86_64/RPMS.mozilla-services/gunicorn-0.11.2-1moz.x86_64.rpm
	cd rpms; wget http://mrepo.mozilla.org/mrepo/5-x86_64/RPMS.mozilla/nginx-0.7.65-4.x86_64.rpm
	mock --install rpms/*
	mock --chroot "python2.6 -m aitc.run"
