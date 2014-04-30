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
  from subprocess import check_output
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
  from gcn_dbinterface import GetGCNConfig, AddGCN, gcninfo
  # Home directory
  homedir = environ['HOME']
  # stop if something looks wrong
except:
  print 'Failed to load modules'
  _exit(-1)

##############################################################################
# Generic Settings
##############################################################################
# link to Swift gcn page
swiftgcnlink="http://j.mp/swiftgcns"
# link to Fermi gcn page
fermigcnlink="http://j.mp/fermigcns"
# link to Agile gcn page
agilegcnlink="http://j.mp/agilegcns"
# link to Integral gcn page
integralgcnlink="http://j.mp/integralgcns"
# link to Maxi gcn page
maxigcnlink="http://j.mp/maxigcns"
# link to KONUS gcn page
konusgcnlink = "http://j.mp/konusgcns"
# link to ICN gcn page
icngcnlink="http://j.mp/icngcns"
# link format
linkfmt = "http://gcn.gsfc.nasa.gov/other/%s.%s"

################################################################################
# Useful functions
################################################################################
def easy_exit(eval,dbcfgs):
  '''
    Function to clean up before exiting and exiting itself
    '''
  if dbcfgs != None:
    nfailed = 0
    for dbcfg in dbcfgs:
      try:
        # Close DB connections
        dbcfg.curs.close()
        dbcfg.dbconn.commit()
      except:
        nfailed += 1
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

def GetBurstTime(wparams):
  btinfo = {'TJD':0 , 'SOD' : 0.0}
  try:
    btinfo['TJD'] = int(GetParam(wparams,'Burst_TJD'))
    btinfo['SOD'] = float(GetParam(wparams,'Burst_SOD'))
  except:
    try:
      btinfo['TJD'] = int(GetParam(wparams,'Event_TJD'))
      btinfo['SOD'] = float(GetParam(wparams,'Event_SOD'))
    except:
      return None
  return btinfo

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
  # INTEGRAL
  gparams = GetGroup(groups,'Test_mpos')
  if gparams != None:
    return GetParam(gparams,'Def_NOT_a_GRB')
  return "unknown"

if __name__ == "__main__":
  ################################################################################
  # Generic Settings
  ################################################################################
  # GCN database
  try:
    gcndbfname = environ['GCNDB']
  except:
    gcndbfname = '%s/gcns.db'%homedir
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


  ################################################################################
  # LOG FILE CONFIGURATION
  ################################################################################
  # Log file name
  # Setup log
  logging.basicConfig(filename=gcnlog,\
                      format='%(asctime)s %(levelname)s: %(message)s',\
                      filemode='a', level=logging.DEBUG)

  ################################################################################
  # Get GCN Database
  ################################################################################
  try:
    dbcfg = GetGCNConfig(gcndbfname,gcndbname)
  except:
    logging.error('Could not read %s'%gcndbname)
    easy_exit(-2,None)
  if dbcfg == None:
    logging.info('GCN DB failed to initialize.')
    easy_exit(-1,[dbcfg])
  ################################################################################
  # Read in data
  ################################################################################
  # Read in data from standard input
  indata = sys.stdin.read()
  xmlstart = indata.find('<?xml')
  # Parse the input
  try:
    xroot = ET.fromstring(indata[xmlstart:])
  except:
    logging.error('Malformed XML (no root):\n%s'%sys.exc_info()[0])
    easy_exit(-2,[dbcfg])


  what = xroot.find('What')
  wparams = what.findall('Param')
  wgroups = what.findall('Group')
  wherewhen = xroot.find('WhereWhen')
  who = xroot.find('Who')

  if what == None:
    logging.error('Malformed XML (no What)')
    easy_exit(-2,[dbcfg])
  if wparams == None:
    logging.error('Malformed XML (no What Params)')
    easy_exit(-2,[dbcfg])
  if wgroups == None:
    logging.error('Malformed XML (no What Groups')
    easy_exit(-2,[dbcfg])
  if wherewhen == None:
    logging.error('Malformed XML (no WhereWhen)')
    easy_exit(-2,[dbcfg])
  if who == None:
    logging.error('Malformed XML (no Who)')
    easy_exit(-2,[dbcfg])

  newgcn = gcninfo()

  newgcn.trigid = GetParam(wparams,'TrigID')
  btinfo = GetBurstTime(wparams)
  try:
    newgcn.trig_tjd = btinfo['TJD']
    newgcn.trig_sod = btinfo['SOD']
  except:
    logging.error('Malformed XML (odd Burst Time)')
    easy_exit(-2,[dbcfg])

  try:
    tinfo = ParseWhereWhen(wherewhen)
  except:
    logging.error('Malformed XML (odd WhereWhen)')
    easy_exit(-2,[dbcfg])
  try:
    newgcn.isnotgrb = IsNotGRB(wgroups)
  except:
    logging.error('Malformed XML (odd GRB status)')
    easy_exit(-2,[dbcfg])
  try:
    newgcn.posunit = tinfo['unit']
    newgcn.ra = tinfo['RA']
    newgcn.dec = tinfo['Dec']
    newgcn.error = tinfo['error']
    newgcn.inten = GetParam(wparams,'Burst_Inten')
    newgcn.intenunit = GetParam(wparams,'Burst_Inten','unit')
    newgcn.mesgtype = what.find('Description').text
    newgcn.updated_date = who.find('Date').text
  except:
    logging.error('Malformed XML')
    easy_exit(-2,[dbcfg])
  # derived
  lcmesgtype = newgcn.mesgtype.lower()
  if lcmesgtype.find('fermi') >= 0:
    newgcn.inst = "Fermi"
    newgcn.link = linkfmt%(newgcn.trigid,'fermi')
  elif lcmesgtype.find('swift') >= 0:
    newgcn.inst = "Swift"
    newgcn.link = linkfmt%(newgcn.trigid,'swift')
  elif lcmesgtype.find('integral') >= 0:
    newgcn.inst = "Integral"
    newgcn.link = linkfmt%(newgcn.trigid,'integral')
  elif lcmesgtype.find('maxi') >= 0:
    newgcn.inst = "MAXI"
    newgcn.link = linkfmt%(newgcn.trigid,'maxi')
  elif lcmesgtype.find('konus') >= 0:
    newgcn.inst = "KONUS"
    newgcn.link = konusgcnlink
  elif lcmesgtype.find('ipn') >= 0:
    newgcn.inst = "IPN"
    newgcn.link = ipngcnlink



  id, status = AddGCN(newgcn,dbcfg)
  # Close DB connections
  dbcfg.curs.close()
  dbcfg.dbconn.commit()
  if status == 0:
    logging.error('Failed to add new GCN:%s %s'%(newgcn.inst,newgcn.trigid))
    gcnalerts = None
  else:
    logging.info('GCN:%s %s'%(newgcn.inst,newgcn.trigid))

  if gcnalerts != None:
    logging.info('Updating Site')
    alrtout, alrterr = check_output(['%s/site-alerter.py'%pathname])
    logging.info(alrtout)
    logging.info(alrterr)

  easy_exit(0,[dbcfg])



