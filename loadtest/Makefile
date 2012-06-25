# build virtualenv
build:
	virtualenv --no-site-packages .
	ln -sf `python -c 'import M2Crypto; print M2Crypto.__file__' | xargs dirname`* ./lib/*/site-packages
	bin/pip install https://github.com/mozilla-services/mozservices/tarball/master
	bin/pip install funkload PyBrowserID mozsvc pyramid_macauth

test:
	bin/fl-run-test stress.py

# run actual funkload bench (called from dist.sh over ssh)
bench:
	while :; do bin/fl-run-bench -f stress.py StressTest.test_app_storage_session; done
