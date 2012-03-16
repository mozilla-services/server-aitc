%define name python26-aitc
%define pythonname AITC
%define version 1.0
%define release 1

Summary: Apps-In-The-Cloud Storage server
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{pythonname}-%{version}.tar.gz
License: MPL
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{pythonname}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Tarek Ziade <tarek@mozilla.com>
BuildRequires: libevent-devel libmemcached-devel
Requires: nginx memcached gunicorn python26 python26-pylibmc python26-setuptools python26-pyramid python26-paste python26-pastedeploy python26-pastescript python26-sqlalchemy python26-simplejson python26-gevent python26-pymysql python26-pymysql_sa python26-mozsvc python26-cornice python26-greenlet
Conflicts: 
Url: https://github.com/mozilla-services/server-aitc

%description
============
Sync Storage
============

This is the Python implementation of the AITC Storage Server.


%prep
%setup -n %{pythonname}-%{version} -n %{pythonname}-%{version}

%build
python2.6 setup.py build

%install

# the config files for Sync apps
mkdir -p %{buildroot}%{_sysconfdir}/aitc
install -m 0644 etc/production.ini %{buildroot}%{_sysconfdir}/aitc/production.ini

# nginx config
mkdir -p %{buildroot}%{_sysconfdir}/nginx
mkdir -p %{buildroot}%{_sysconfdir}/nginx/conf.d
install -m 0644 etc/aitc.nginx.conf %{buildroot}%{_sysconfdir}/nginx/conf.d/aitc.conf

# logging
mkdir -p %{buildroot}%{_localstatedir}/log
touch %{buildroot}%{_localstatedir}/log/aitc.log

# the app
python2.6 setup.py install --single-version-externally-managed --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

%post
touch %{_localstatedir}/log/aitc.log
chown nginx:nginx %{_localstatedir}/log/aitc.log
chmod 640 %{_localstatedir}/log/aitc.log

%files -f INSTALLED_FILES

%attr(640, nginx, nginx) %ghost %{_localstatedir}/log/aitc.log

%dir %{_sysconfdir}/aitc/

%config(noreplace) %{_sysconfdir}/aitc/*
%config(noreplace) %{_sysconfdir}/nginx/conf.d/aitc.conf

%defattr(-,root,root)
