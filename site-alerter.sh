#!/bin/bash
export PYTHONPATH="${HOME}/opt/lib/python2.6/site-packages:${HOME}/devl/gcn-parser"

# ENV VARS #
ttag="testing"
export LOGDIR="${HOME}/logs/${ttag}"
## bitly ##
export BITLYAPI="${HOME}/.bitlyapi"
## site-alerter ##
export GCNDB="${HOME}/public_html/${ttag}/gcns.db"
export GCNDBNAME="GCNs"
### CONFIG ###
export SALERTDB="${HOME}/public_html/${ttag}/alerts.db"
export SALERTDBNAME="alerts"
export SALERTCFG="${HOME}/.site-alerter-cfg"
export SALERTLOG="${LOGDIR}/site-alerter.log"
### SITE ###
export GCNSITE="HAWC"
export GCNSITELAT="+19.0304954539937"
export GCNSITELONG="-97.2698484177274"
export GCNSITEHORIZON="45.0"
### WEB ###
export GCNHTTP="http://umdgrb.umd.edu/~bbaugh/${ttag}"
export GCNSMTP="umdgrb.umd.edu"
export GCNWEB="${HOME}/public_html/${ttag}"
export GCNSITELINK="http://j.mp/hawcgcnwatch"
export NOUTGCNS="100"
## site-alerter-daemon ##
export GCNDAEMONLOG="${LOGDIR}/gcn-daemon.log"
export GCNDAEMONLOCK="${HOME}/locks/site-alerter-daemon.lock"

export GCNDBSRV="umdgrb.umd.edu"
export GCNDBOSRV="/home/bbaugh/public_html/${ttag}/gcns.db"
export GCNWEBOSRV="/home/bbaugh/public_html/${ttag}"

export GCNINTER="60"

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


