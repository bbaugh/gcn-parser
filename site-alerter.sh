#!/bin/bash
export PYTHONPATH="${HOME}/opt/lib/python2.6/site-packages:${HOME}/devl/gcn-parser"

# ENV VARS #
export LOGDIR="${HOME}/logs"
## bitly ##
export BITLYAPI="${HOME}/.bitlyapi"
## site-alerter ##
export GCNDB="${HOME}/public_html/gcns.db"
export GCNDBNAME="GCNs"
### CONFIG ###
export SALERTDB="${HOME}/public_html/alerts.db"
export SALERTDBNAME="alerts"
export SALERTCFG="${HOME}/.site-alerter-cfg"
export SALERTLOG="${LOGDIR}/site-alerter.log"
### SITE ###
export GCNSITE="HAWC"
export GCNSITELAT="+19.0304954539937"
export GCNSITELONG="-97.2698484177274"
export GCNSITEHORIZON="45.0"
### WEB ###
export GCNHTTP="http://umdgrb.umd.edu/~bbaugh"
export GCNSMTP="umdgrb.umd.edu"
export GCNWEB="${HOME}/public_html"
export GCNSITELINK="http://j.mp/hawcgcnwatch"
export NOUTGCNS="100"
## site-alerter-daemon ##
export GCNDAEMONLOG="${LOGDIR}/gcn-daemon.log"
export GCNDAEMONLOCK="${HOME}/locks/site-alerter-daemon.lock"

export GCNDBSRV="umdgrb.umd.edu"
export GCNDBOSRV="/home/bbaugh/public_html/gcns.db"
export GCNWEBOSRV="/home/bbaugh/public_html"

export GCNINTER="60"

state=0
oldpid=0
if [ -f $GCNDAEMONLOCK ]; then
  read oldpid < $GCNDAEMONLOCK
  if [ -d "/proc/${oldpid}" ]; then
    state=1
  else
    echo "Removing outdated GCNDAEMONLOCK"
    rm $GCNDAEMONLOCK
  fi
fi

function killjob()
{
  if [ ${#} -eq 1 ]; then
    kpid=${1}
    ntkls=0
    while true; do
      if [ ${ntkls} -gt 10 ]; then
        kill -9 ${kpid}
        break
      fi
      if [ -d "/proc/${kpid}" ]; then
        kill ${kpid}
        ntkls=$(( ntkls +1 ))
        sleep 10
      else
        break
      fi
    done
    if [ -d "/proc/${kpid}" ]; then
      echo "Failed to kill job(${kpid})!"
      return 0
    fi
    return 1
  else
    echo "Invalid use of killjob!"
    return 0
  fi
}


script=`basename ${0}`
case "$1" in
  start)
    if [ "${state}" -eq "1" ]; then
      echo "Already running"
    else
      echo "Starting site-alerter"
      # Start the daemon
      ${HOME}/devl/gcn-parser/site-alerter-daemon.py start
    fi
    ;;
  check)
    if [ "${state}" -eq "0" ]; then
      echo "Stopped"
    else
      echo "Running"
    fi
    ;;
  stop)
    if [ "${state}" -eq "1" ]; then
      echo "Stopping"
      # Stop the daemon
      ${HOME}/devl/gcn-parser/site-alerter-daemon.py stop
      if [ -d "/proc/${oldpid}" ]; then
        killjob ${oldpid}
      fi

    else
      echo "Not running site-alerter"
    fi
    ;;
  restart)
    echo "Restarting site-alerter"
    if [ "${state}" -eq "1" ]; then
      ${HOME}/devl/gcn-parser/site-alerter-daemon.py restart
    else
      ${HOME}/devl/gcn-parser/site-alerter-daemon.py start
    fi
    ;;
  *)
    # Refuse to do other stuff
    echo "Usage: ${script} {start|stop|restart}"
    exit 1
    ;;
esac

exit 0


