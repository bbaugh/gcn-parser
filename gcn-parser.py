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
  import sys, re, time, logging
  from os import environ, path, _exit, makedirs, stat
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
  from gcn_dbinterface import GetConfig, AddGCN, gcninfo
  # Home directory
  homedir = environ['HOME']
  # stop if something looks wrong
except:
  print 'Failed to load modules'
  _exit(-1)

################################################################################
# Useful functions
################################################################################
def easy_exit(eval):
  '''
    Function to clean up before exiting and exiting itself
  '''
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

if __name__ == "__main__":
  ################################################################################
  # Generic Settings
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

  # Get log file name
  try:
    gcnlog = environ['GCNLOG']
  except:
    gcnlog = '%s/logs/gcn-parser.log'%homedir

  try:
    gcnalerts = environ['GCNALERTS']
  except:
    gcnalerts = None

  curtime = time.strftime('%Y-%m-%d %H:%M:%S')

  ################################################################################
  # LOG FILE CONFIGURATION
  ################################################################################
  # Log file name
  # Setup log
  logging.basicConfig(filename=gcnlog,\
                      format='%(asctime)s %(levelname)s: %(message)s',\
                      filemode='a', level=logging.DEBUG)

  ################################################################################
  # Get Database
  ################################################################################
  try:
    dbcfg = GetConfig(gcnbfname,gcndbname)
  except:
    logging.error('Could not read %s'%gcndbname)
    easy_exit(-2)
  ################################################################################
  # Read in data
  ################################################################################
  # Read in data from standard input
  indata = sys.stdin.read()
  # Parse the input
  try:
    xroot = ET.fromstring(indata)
  except:
    logging.error('Malformed XML (no root)')
    easy_exit(-2)


  what = xroot.find('What')
  wparams = what.findall('Param')
  wgroups = what.findall('Group')
  wherewhen = xroot.find('WhereWhen')

  if what == None:
    logging.error('Malformed XML (no What)')
    easy_exit(-2)
  if wparams == None:
    logging.error('Malformed XML (no What Params)')
    easy_exit(-2)
  if wgroups == None:
    logging.error('Malformed XML (no What Groups')
    easy_exit(-2)
  if wherewhen == None:
    logging.error('Malformed XML (no WhereWhen)')
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
    lcmesgtype = newgcn.mesgtype.lower()
    if lcmesgtype.find('fermi') >= 0:
      if lcmesgtype.find('fermi-lat') >= 0:
        newgcn.inst = "Fermi-LAT"
      elif lcmesgtype.find('fermi-gbm') >= 0:
        newgcn.inst = "Fermi-GBM"
      else:
        newgcn.inst = "Fermi"
    elif lcmesgtype.find('swift') >= 0:
      if lcmesgtype.find('swift-uvot') >= 0:
        newgcn.inst = "Swift-UVOT"
      elif lcmesgtype.find('swift-xrt') >= 0:
        newgcn.inst = "Swift-XRT"
      elif lcmesgtype.find('swift-bat') >= 0:
        newgcn.inst = "Swift-BAT"
      else:
        newgcn.inst = "Swift"
    elif lcmesgtype.find('integral') >= 0:
      newgcn.inst = "Integral"
    elif lcmesgtype.find('maxi') >= 0:
      newgcn.inst = "MAXI"
    elif lcmesgtype.find('icn') >= 0:
      newgcn.inst = "ICN"
    newgcn.updated = 1

  except:
    logging.error('Malformed XML')
    easy_exit(-2)


  id, status = AddGCN(newgcn,dbcfg)
  # Close DB connections
  dbcfg.gcncurs.close()
  dbcfg.gcndbconn.commit()
  if status == 0:
    logging.error('Failed to add new GCN:%s %s'%(newgcn.inst,newgcn.trigid))
    gcnalerts = None
  else:
    logging.info('GCN:%s %s'%(newgcn.inst,newgcn.trigid))

  if gcnalerts != None:
    logging.info('Updating Site')
    call(['%s/site-alerter.py'%pathname],stdout=log,stderr=STDOUT)

  easy_exit(0)



