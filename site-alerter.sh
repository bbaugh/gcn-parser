#!/bin/bash
export PYTHONPATH="${HOME}/opt/lib/python2.6/site-packages:${HOME}/devl/gcn-parser"

#----------GCN VARS--------
export GCNSMTP="umdgrb.umd.edu"
export GCNHTTP="http://umdgrb.umd.edu/~bbaugh/testing"
export GCNWEB="${HOME}/public_html/testing"
export GCNDB="${HOME}/public_html/testing/gcns.db"
export GCNDBNAME="GCNs"
export GCNDBOSRV="/home/bbaugh/public_html/testing/gcns.db"
export GCNDBSRV="umdgrb.umd.edu"
export GCNWEBOSRV="/home/bbaugh/public_html/testing"
export GCNDAEMONLOCK="/tmp/site-alerter-daemon.lock"
export SALERTLOG="${HOME}/logs/site-alerter.log"
script=`basename ${0}`
case "$1" in
  start)
    if [ -a "${GCNDAEMONLOCK}" ]; then
      echo "Already running site-alerter"
    else
      echo "Starting site-alerter"
      # Start the daemon
      python ${HOME}/devl/gcn-parser/site-alerter-daemon.py start
    fi
    ;;
  check)
    if [ ! -a "${GCNDAEMONLOCK}" ]; then
      echo "Starting site-alerter"
      # Start the daemon
      python ${HOME}/devl/gcn-parser/site-alerter-daemon.py start
    fi
    ;;
  stop)
    if [ -a "${GCNDAEMONLOCK}" ]; then
      echo "Stopping site-alerter"
      # Stop the daemon
      python ${HOME}/devl/gcn-parser/site-alerter-daemon.py stop
    else
      echo "Not running site-alerter"
    fi
    ;;
  restart)
    echo "Restarting site-alerter"
    python ${HOME}/devl/gcn-parser/site-alerter-daemon.py restart
    ;;
  *)
    # Refuse to do other stuff
    echo "Usage: ${script} {start|stop|restart}"
    exit 1
    ;;
esac

exit 0


