#!/usr/bin/env python
################################################################################
#  site-alerter-daemon.py
#  
#
#  Created by Brian Baughman on 3/7/13.
#  Copyright 2013 Brian Baughman. All rights reserved.
################################################################################
try:
  import sys, re, time, threading
  from daemon import runner
  from os import environ, path, _exit, makedirs, stat, devnull, access, X_OK
  from subprocess import call, STDOUT, PIPE, Popen
  pathname = path.dirname(sys.argv[0])
except:
  print 'Failed to load base modules'
  sys.exit(-1)

try:
  try:
    import xml.etree.ElementTree as ET
  except:
    try:
      import elementtree.ElementTree as ET
    except:
      print 'Failed to load ElementTree'
      _exit(-1)
  import smtplib
  from email import MIMEText
  from gcn_dbinterface import GetConfig, MakeEntry, gcninfo
  import matplotlib
  matplotlib.use('agg')
  from matplotlib import dates as mpldates
  from matplotlib.cbook import is_numlike
  from matplotlib import rcParams
  from matplotlib.pyplot import draw, figure
  from matplotlib.dates import datestr2num,date2num
  import matplotlib.image as image
  from numpy import deg2rad, rad2deg, arange, asarray, array, pi, where, iterable
  import ephem
  from bitly import shorten
  
  # Home directory
  homedir = environ['HOME']
  # stop if something looks wrong
except:
  print 'Failed to load modules'
  _exit(-1)

# Check SSH
devnullfobj = open(devnull,'w')
if call(['rsync','--version'],stdout=devnullfobj,stderr=devnullfobj):
  print 'rsync not available!'
  _exit(-1)
devnullfobj.close()


if not path.isfile('%s/site-alerter.py'%pathname):
  print 'Cannot file site-alerter.py!'
  _exit(-1)

if not access('%s/site-alerter.py'%pathname,X_OK):
  print 'Cannot execute site-alerter.py!'
  _exit(-1)
################################################################################
# Environment Setup
################################################################################
# GCN database
try:
  gcnbfname = environ['GCNDB']
except:
  gcnbfname = '%s/gcns.db'%homedir
try:
  gcndbname = environ['GCNDBNAME']
except:
  gcndbname = "gcns"

try:
  gcndaemonlog = environ['GCNDAEMONLOG']
except:
  gcndaemonlog = '%s/logs/gcn-daemon.log'%homedir

try:
  gcndaemonlock = environ['GCNDAEMONLOCK']
except:
  gcndaemonlock = '/tmp/site-alerter-daemon.lock'
# GCN database
try:
  gcndbosrv = environ['GCNDBOSRV']
except:
  print 'GCNDBOSRV is not defined!'
  _exit(-2)

gcndbfname = path.basename(gcndbosrv)

try:
  gcnwebosrv = environ['GCNWEBOSRV']
except:
  print 'GCNWEBOSRV is not defined!'
  _exit(-2)

try:
  gcndbsrv = environ['GCNDBSRV']
except:
  print 'GCNDBSRV is not defined!'
  _exit(-2)

# Get web base
try:
  gcnhttp = environ['GCNHTTP']
except:
  print 'GCNHTTP not set!'
  _exit(-2)

# GCNSMTP
try:
  gcnsmtp = environ['GCNSMTP']
except:
  print 'GCNSMTP not set!'
  _exit(-2)

try:
  gcnweb = environ['GCNWEB']
except:
  gcnweb = '%s/public_html'%homedir

try:
  gcninter = float(environ['GCNINTER'])
except:
  gcninter = 60
################################################################################
# App to run
################################################################################

class App():
  def __init__(self,log=devnull,inter=60,
               pidfile='/tmp/site-alerter-daemon.lock'):
    self.stdin_path = '/dev/null'
    self.stdout_path = log
    self.stderr_path = '/dev/tty'
    self.pidfile_path =  pidfile
    self.pidfile_timeout = inter+1
    self.umask = 0022
    self.inter = inter
    self.modtime = None
    self.buildsite = False
  def run(self):
    self.Check()

  def UpdateDB(self):
    devnullfobj = open(devnull,'w')
    call(['rsync','-azq','%s:%s'%(gcndbsrv,gcndbosrv),'%s/'%gcnweb],\
         stdout=devnullfobj,stderr=devnullfobj)
    devnullfobj.close()
    if path.isfile('%s/%s'%(gcnweb,gcndbfname)):
      cmt = path.getmtime('%s/%s'%(gcnweb,gcndbfname))
      if self.modtime == None or self.modtime != cmt:
        self.modtime = cmt
        self.buildsite = True
  
  def SiteAlerter(self):
    call(['%s/site-alerter.py'%pathname])


  def PushBack(self):
    devnullfobj = open(devnull,'w')
    call(['rsync','-azq','--exclude=%s'%gcndbfname,\
          '%s/'%gcnweb,\
          '%s:%s'%(gcndbsrv,gcnwebosrv)],\
         stdout=devnullfobj,stderr=devnullfobj)
    devnullfobj.close()
  
  def Check(self):
    '''
      Function which calls itself every interval
      '''
    self.UpdateDB()
    if self.buildsite:
      self.SiteAlerter()
      self.PushBack()
      self.buildsite = False
    # Wait for inter then call again
    threading.Timer(self.inter, self.Check).start()


# Start daemon
if __name__ == "__main__":
  app = App(log=gcndaemonlog,inter=gcninter,pidfile=gcndaemonlock)
  daemon_runner = runner.DaemonRunner(app)
  daemon_runner.daemon_context.files_preserve=[gcndaemonlog]
  daemon_runner.do_action();

