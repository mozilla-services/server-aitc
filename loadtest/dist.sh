#!/bin/bash

workers="client4.scl2.svc.mozilla.com client5.scl2.svc.mozilla.com client6.scl2.svc.mozilla.com client7.scl2.svc.mozilla.com client8.scl2.svc.mozilla.com client9.scl2.svc.mozilla.com"
dest_dir="$HOME/aitc-loadtest"
source_dir=$(dirname $0)

if [ "$1" = "clean" ]; then
    echo "==> cleaning up existing loadtest virtualenvs"
    xapply -xP10 "ssh %1 rm -rf $dest_dir" $workers
fi

trap "echo ==> 'killing bench runs'; xapply 'ssh %1 killall fl-run-bench' $workers" EXIT

echo "==> killing existing bench runs"
xapply -xP10 "ssh %1 killall fl-run-bench 2\>/dev/null" $workers

echo "==> syncing files to workers"
xapply -xP10 "rsync $source_dir/{StressTest.conf,stress.py,Makefile} %1:$dest_dir/" $workers

echo "==> building virtualenvs"
xapply -xP10 "ssh %1 cd $dest_dir \; rm -f loadtest\* \; make build" $workers

echo "==> running load"
while :; do
    xapply -xP10 "ssh %1 cd $dest_dir \; make bench" $workers
done
