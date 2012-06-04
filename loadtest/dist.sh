#!/bin/sh

workers="client4.scl2.svc.mozilla.com client5.scl2.svc.mozilla.com client6.scl2.svc.mozilla.com client7.scl2.svc.mozilla.com client8.scl2.svc.mozilla.com client9.scl2.svc.mozilla.com"
dest_dir="$HOME/aitc-loadtest"
source_dir=$(dirname $0)

trap "echo ==> 'killing bench runs'; xapply 'ssh %1 killall fl-run-bench' $workers" EXIT

echo "==> killing existing bench runs"
xapply "ssh %1 killall fl-run-bench" $workers

echo "==> syncing files to workers"
xapply "rsync $source_dir/{StressTest.conf,stress.py,Makefile,aitc-1.0.stage} %1:$dest_dir/" $workers

echo "==> building virtualenvs"
xapply "ssh %1 cd $dest_dir \; rm loadtest*\; make build" $workers

echo "==> running load"
while :; do
    xapply -xP10 "ssh %1 cd $dest_dir \; make bench" $workers
done
