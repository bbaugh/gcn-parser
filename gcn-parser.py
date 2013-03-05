#!/usr/bin/env python
################################################################################
#  gcn-parser.py
#  Parses XML notices sent via email by the GCN (http://gcn.gsfc.nasa.gov)
#  creates a sqlite database with a subset of the data sent and calculates the
#  zenith angle of the GCN.
#
#  Created by Brian Baughman on 2013/02/27.
#  Copyright 2013 Brian Baughman. All rights reserved.
################################################################################
################################################################################
# Load needed modules
################################################################################
try:
  import sys, re, time
  from os import environ, remove, path, _exit, makedirs, stat
  from subprocess import call, STDOUT
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
  from gcn_dbinterface import gcncurs, gcndbconn, gcndbname, \
    gcndbstruct, MakeEntry, gcninfo, AddGCN
  # Home directory
  homedir = environ['HOME']
  # stop if something looks wrong
except:
  print 'Failed to load modules'
  _exit(-1)

################################################################################
# Generic Settings
################################################################################

# Get log file name
try:
  gcnlog = environ['GCNLOG']
except:
  gcnlog = '%s/logs/gcnalerts.log'%homedir

curtime = time.strftime('%Y-%m-%d %H:%M:%S')
################################################################################
# Lock file checking
################################################################################
# Get lock file name
try:
  gcnlock = environ['GCNLOCK']
except:
  gcnlock = '%s/.gcnlock'%homedir

# Check that the lock file is not set
try:
  lock = open(gcnlock, 'r')
  lock.close()
  print "Already running...\n"
  _exit(-1)
except:
  lock = open(gcnlock, 'w')
  lock.write('on')
  lock.close()

################################################################################
# LOG FILE CONFIGURATION
################################################################################
# Log file name
# Setup log
try:
  log = open(gcnlog, 'a')
  print '%s: Log file: %s\n'%(curtime,gcnlog)
except:
  print '%s: Cannot open log file: %s\n'%(curtime,gcnlog)
  log = sys.stdout

################################################################################
# Useful functions
################################################################################
def easy_exit(eval):
  '''
    Function to clean up before exiting and exiting itself
  '''
  gcndbconn.commit()
  try:
    lock = open(gcnlock, 'r')
    lock.close()
    remove(gcnlock)
    try:
      lock = open(gcnlock, 'r')
      lock.close()
      log.write('%s : The lock is still here...'%curtime)
    except:
      good = True
  finally:
    try:
      log.close()
    except:
      _exit(eval)
    _exit(eval)

def dircheck(dir):
  '''
    Checks if the given directory exists, if not it attempts to create it.
  '''
  try:
    stat(dir)
  except:
    makedirs(dir)
  try:
    stat(dir)
    return True
  except:
    return False


def GetParam(params,name,rattrib='value'):
  '''
    Returns an attribute value or None (if not found) from a list of 'Param's given.
  '''
  for param in params:
    try:
      attribs = param.attrib
      if attribs['name'] == name:
        return attribs[rattrib]
    except:
      continue
  return None

def GetGroup(groups,name):
  '''
    Returns 'Param's of group or None (if not found) from a list of 'Group's given.
  '''
  for groups in groups:
    try:
      attribs = groups.attrib
      if attribs['name'] == name:
        return groups.findall('Param')
    except:
      continue
  return None

def ParseWhereWhen(wherewhen):
  obsdatloc = wherewhen.find('ObsDataLocation')
  if obsdatloc == None:
    return None
  obsloc = obsdatloc.find('ObservationLocation')
  if obsloc == None:
    return None
  astrocoords = obsloc.find('AstroCoords')
  if astrocoords == None:
    return None
  oinfo = {'coord_system_id':None,'time' : None,\
           'RA': None, 'Dec': None, 'error': None, 'unit': None }
  try:
    oinfo['coord_system_id'] = astrocoords.attrib['coord_system_id']
    oinfo['time'] = astrocoords.find('Time').find('TimeInstant').find('ISOTime').text.strip()
    posobj = astrocoords.find('Position2D')
    oinfo['unit'] = posobj.attrib['unit']
    posarr = posobj.find('Value2')
    name1 = posobj.find('Name1').text.strip()
    name2 = posobj.find('Name2').text.strip()
    if name1 == 'RA':
      oinfo['RA'] = posarr.find('C1').text.strip()
    elif name2 == 'RA':
      oinfo['RA'] = posarr.find('C2').text.strip()
    if name1 == 'Dec':
      oinfo['Dec'] = posarr.find('C1').text.strip()
    elif name2 == 'Dec':
      oinfo['Dec'] = posarr.find('C2').text.strip()
    if oinfo['RA'] == None or oinfo['Dec'] == None:
      return None
    oinfo['error'] = posobj.find('Error2Radius').text.strip()
    return oinfo
  except:
    return None
  return None

def IsNotGRB(groups):
  # Fermi
  gparams = GetGroup(groups,'Trigger_ID')
  if gparams != None:
    return GetParam(gparams,'Def_NOT_a_GRB')
  # Swift
  gparams = GetGroup(groups,'Solution_Status')
  if gparams != None:
    return GetParam(gparams,'Def_NOT_a_GRB')
  return None



################################################################################
# Read in data
################################################################################
# Read in data from standard input
indata = sys.stdin.read()
# Parse the input
try:
  xroot = ET.fromstring(indata)
except:
  log.write('%s: Malformed XML (no root)\n'%(curtime))
  print indata
  easy_exit(-2)


what = xroot.find('What')
wparams = what.findall('Param')
wgroups = what.findall('Group')
wherewhen = xroot.find('WhereWhen')

if what == None:
  log.write('%s: Malformed XML (no What)\n'%(curtime))
  easy_exit(-2)
if wparams == None:
  log.write('%s: Malformed XML (no What Params)\n'%(curtime))
  easy_exit(-2)
if wgroups == None:
  log.write('%s: Malformed XML (no What Groups\n'%(curtime))
  easy_exit(-2)
if wherewhen == None:
  log.write('%s: Malformed XML (no WhereWhen)\n'%(curtime))
  easy_exit(-2)

newgcn = gcninfo()
try:
  newgcn.trigid = GetParam(wparams,'TrigID')
  tinfo = ParseWhereWhen(wherewhen)
  newgcn.datestr = tinfo['time']
  newgcn.isnotgrb = IsNotGRB(wgroups)
  newgcn.posunit = tinfo['unit']
  newgcn.ra = tinfo['RA']
  newgcn.dec = tinfo['Dec']
  newgcn.error = tinfo['error']
  newgcn.inten = GetParam(wparams,'Burst_Inten')
  newgcn.intenunit = GetParam(wparams,'Burst_Inten','unit')
  newgcn.mesgtype = what.find('Description').text
  # derived
  newgcn.sent = 0
  
  gcndbstruct = newgcn.__dbstruct__
  print '============================================'
  for cattr in gcndbstruct.keys():
    print '%s : %s'%(cattr,newgcn.__getattribute__(cattr))
  print '============================================'
except:
  log.write('%s: Malformed XML\n'%(curtime))
  easy_exit(-2)


id, status = AddGCN(newgcn)
if status == 0:
  log.write('%s: Failed to add new GCN:%s %s\n'%(curtime,cgcn.inst,cgcn.trignumraw))

# Close DB connections
gcncurs.close()
gcndbconn.commit()
call(['python','%s/site-alerter.py'%pathname],stdout=log,stderr=STDOUT)

easy_exit(0)



