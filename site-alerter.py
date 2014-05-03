#!/usr/bin/env python
################################################################################
#  site-alerter.py
#  Constructs a XML list of GCNs for a given site and sends alerts
#
#  Created by Brian Baughman on 3/4/13.
#  Copyright 2013 Brian Baughman. All rights reserved.
################################################################################
################################################################################
# Load needed modules
################################################################################
try:
  import sys, re, time, logging
  from os import environ, path, _exit, makedirs, stat, access, R_OK, W_OK
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
  from gcn_dbinterface import GetGCNConfig,GetConfig, MakeEntry, baseentry,\
    gcninfo
  from bitly import shorten
  from timeConv import tjd2dttm, secInday
  from coordConv import *
  from datetime import datetime
  from numpy import deg2rad, rad2deg
  # Home directory
  homedir = environ['HOME']
  # stop if something looks wrong
except:
  print 'Failed to load modules'
  _exit(-1)

##############################################################################
# Generic Settings
##############################################################################
# Update date format
updfmt = '%Y-%m-%dT%H:%M:%S'
# Subject of email format
sbjctfmt = 'GCN at %s in %s FOV'
# Content of email format
txtfmt = '%s trigger %s was in the FOV of %s at %.2f degrees from Zenith. More info at %s and %s'
# Define some regexes
hrefre = re.compile("<[^>]*href=([^\ \"'>]+)>")
################################################################################
# Define DB structure
################################################################################
class alertinfo(baseentry):
  def __init__(self):
    self.id = "null"
    # Read directly
    self.trigid = "unset"
    self.trig_tjd = 0
    self.trig_sod = 0.
    #    self.trig_date = "unset"
    self.updated_date = "unset"
    self.sent = 0
    self.setDBType()

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

def gettxt(cinfo,curzen,sitetag,sitelink):
  '''
    Generated formatted text for email alert
  '''
  txt = txtfmt%(cinfo.inst.capitalize(),\
                cinfo.trigid,\
                sitetag,\
                curzen,\
                shorten(cinfo.link),\
                sitelink)
  return txt

def email(sender,recipient,subject,text):
  msg = MIMEText.MIMEText(text)
  # sender == the sender's email address
  # recipient == the recipient's email address
  msg['Subject'] = subject
  msg['From'] = sender
  if iterable(recipient):
    msg['To'] = ','.join(recipient)
  else:
    msg['To'] = recipient

  # Send the message via our own SMTP server, but don't include the
  # envelope header.
  s = smtplib.SMTP(gcnsmtp)
  s.sendmail(sender, msg['To'].split(','), msg.as_string())
  s.quit()

if __name__ == "__main__":
  # GCN database
  try:
    gcndbfname = environ['GCNDB']
  except:
    gcndbfname = '%s/gcns.db'%homedir
  try:
    gcndbname = environ['GCNDBNAME']
  except:
    gcndbname = "gcns"
  # Alerts database
  try:
    salertdbfname = environ['SALERTDB']
  except:
    salertdbfname = '%s/alerts.db'%homedir
  try:
    salertdbname = environ['SALERTDBNAME']
  except:
    salertdbname = "alerts"

  # Alerts config
  try:
    salertcfg = environ['SALERTCFG']
  except:
    salertcfg = None
  # Log file name
  try:
    salertlog = environ['SALERTLOG']
  except:
    salertlog = '%s/logs/site-alerter.log'%homedir

  # Site Setup
  try:
    sitetag = environ['GCNSITE']
  except:
    sitetag = 'HAWC'
  try:
    obslat = deg2rad(float(environ['GCNSITELAT']))
  except:
    obslat = deg2rad(+19.0304954539937)
  try:
    obslon = float(deg2rad(environ['GCNSITELONG']))
  except:
    obslon = deg2rad(-97.2698484177274)
  try:
    obshorizon = float(environ['GCNSITEHORIZON'])
  except:
    obshorizon = float(45.000)

  ##############################################################################
  # LOG FILE CONFIGURATION
  ##############################################################################
  # Log file name
  logging.basicConfig(filename=salertlog,\
                      format='%(asctime)s %(levelname)s: %(message)s',\
                      filemode='a', level=logging.DEBUG)
  ################################################################################
  # Get GCN Database
  ################################################################################
  try:
    dbcfg = GetGCNConfig(gcndbfname,gcndbname)
  except:
    logging.error('Could not read %s'%gcndbname)
    easy_exit(-1,None)
  if dbcfg == None:
    logging.info('GCN DB failed to initialize.')
    easy_exit(-1,None)
  ##############################################################################
  # Get Alerts Database
  ##############################################################################
  try:
    alertdbcfg = GetConfig(salertdbfname,salertdbname,alertinfo)
  except:
    logging.error('Could not read %s'%salertdbname)
    easy_exit(-1,[dbcfg])
  if alertdbcfg == None:
    logging.info('Alert DB failed to initialize.')
    easy_exit(-1,[dbcfg])

  ##############################################################################
  # Alerts config
  ##############################################################################
  # Sender of emails
  sender = None
  # Reciepents of email
  recipients = None
  # Read configuration file
  try:
    salertcfgif = open(salertcfg,'r')
    cfglines = salertcfgif.readlines()
    salertcfgif.close()
    if len(cfglines) >= 2:
      sender = cfglines[0].strip()
      recipients = cfglines[1].strip().split(',')
    if len(recipients) <=0 :
      sender = None
      recipients = None
  except:
    if salertcfg != None:
      logging.error('Cannot read sender/recipients from: %s\n'%(salertcfg))
      easy_exit(-3,[dbcfg,alertdbcfg])
    else:
      logging.debug('No alerts will be sent')

  ##############################################################################
  # Environment Settings
  ##############################################################################
  # Get web base
  try:
    gcnhttp = environ['GCNHTTP']
  except:
    logging.error('GCNHTTP not set!')
    easy_exit(-2,[dbcfg,alertdbcfg])

  # GCNSMTP
  try:
    gcnsmtp = environ['GCNSMTP']
  except:
    logging.error( 'GCNSMTP not set!')
    easy_exit(-2,[dbcfg,alertdbcfg])

  # Get web base
  try:
    gcnweb = environ['GCNWEB']
  except:
    gcnweb = '%s/public_html'%homedir

  try:
    sitelink = environ['GCNSITELINK']
  except:
    sitelink = gcnhttp

  # Number of recent GCNs to output
  try:
    nrecent = int(environ['NOUTGCNS'])
  except:
    nrecent = 100
  ################################################################################
  # Meat
  ################################################################################

  # Grab recents
  trig_tjd = 0
  trig_sod = 1
  id = 2
  trigid = 3
  updated_date = 4
  recentstr = "SELECT DISTINCT trig_tjd,trig_sod,id,trigid,updated_date"
  recentstr += " FROM %s ORDER BY trig_tjd DESC, trig_sod DESC LIMIT %i ;"%(dbcfg.dbname,\
                                                              nrecent)
  dbcfg.curs.execute(recentstr)
  recent = dbcfg.curs.fetchall()

  # XML header
  root = ET.Element("xml")
  root.attrib['version'] = "1.0"
  gcns = ET.SubElement(root, "gcns")

  a_id = alertdbcfg.dbstruct['id']['index']
  a_sent = alertdbcfg.dbstruct['sent']['index']
  a_updated_date = alertdbcfg.dbstruct['updated_date']['index']
  for row in recent:
    # Check if this entry has been updated
    upd = False
    sentflg = 0
    qstr = "SELECT * FROM %s WHERE trig_tjd=%s AND trigid='%s';"
    qstr = qstr%(alertdbcfg.dbname,row[trig_tjd],row[trigid])
    alertdbcfg.curs.execute(qstr)
    camtchs = alertdbcfg.curs.fetchall()
    if  len(camtchs) == 0:
      '''
        Add new entry
      '''
      nAlert = alertinfo()
      nAlert.trigid = row[trigid]
      nAlert.trig_tjd = row[trig_tjd]
      nAlert.trig_sod = row[trig_sod]
      nAlert.updated_date = row[updated_date]
      nAlert.sent = 0
      carr = [nAlert.__getattribute__(cattr) for cattr in alertdbcfg.dbstruct.keys() ]
      cintstr = alertdbcfg.inststr%tuple(carr)
      alertdbcfg.curs.execute(cintstr)
      alertdbcfg.dbconn.commit()
      alertdbcfg.curs.execute(qstr)
      camtchs = alertdbcfg.curs.fetchall()
      upd = True
    elif len(camtchs) > 1:
      '''
        This should never happen so assume it is an error and skip
      '''
      logging.info('Found multiple entries for %s'%row[trigid])
      continue
    rEUD = datetime.strptime(str(row[updated_date]),updfmt)
    for m in camtchs:
      mEUD =  datetime.strptime(str(m[a_updated_date]),updfmt)
      if rEUD > mEUD:
        upd = True
      sentflg += m[a_sent]

    # Calculate position at site
    qstr = "SELECT * FROM %s WHERE id=%s;"%(dbcfg.dbname,row[id])
    dbcfg.curs.execute(qstr)
    cmtchs = dbcfg.curs.fetchall()
    curinfo = MakeEntry(cmtchs[0],gcninfo,dbcfg.dbstruct)

    evtTime = tjd2dttm(curinfo.trig_tjd + curinfo.trig_sod/secInday)
    evtRA = deg2rad(float(curinfo.ra))
    evtDec = deg2rad(float(curinfo.dec))
    evtAlt,evtAz = eq2horz(obslat,obslon,evtTime,evtRA,evtDec)
    evtdZenith = 90. - rad2deg(evtAlt)
    if upd:
      logging.debug("Updated %s"%(curinfo.trigid))
      ustr = "UPDATE %s SET updated_date='%s' WHERE id='%s';"
      ustr = ustr%(alertdbcfg.dbname, row[updated_date], camtchs[0][a_id])
      try:
        alertdbcfg.curs.execute(ustr)
        alertdbcfg.dbconn.commit()
      except:
        logging.error( 'Failed to update Alert DB.')

    if evtdZenith < obshorizon and sentflg == 0:
      sbjct = sbjctfmt%(str(evtTime),sitetag)
      txt = gettxt(curinfo,evtdZenith,sitetag,sitelink)
      ustr = "UPDATE %s SET sent=1 WHERE id='%s';"%(alertdbcfg.dbname,\
                                                     camtchs[0][a_id])
      try:
        alertdbcfg.curs.execute(ustr)
        alertdbcfg.dbconn.commit()
        email(sender,recipients,sbjct,txt)
        logging.info( 'Sent: %s'%(sbjct))
      except:
        logging.error( 'Failed to send notification or update Alert DB.')
        continue


    for cattr in dbcfg.dbstruct.keys():
      cursubelm = ET.SubElement(curgcn,cattr)
      cursubelm.text = str(curinfo.__getattribute__(cattr))
    cursubelm = ET.SubElement(curgcn,'trig_date')
    cursubelm.text = str(evtTime)


  # Save XML
  logging.info( 'Updating XML')
  xmlfname = '%s/gcns.xml'%gcnweb
  fout = open(xmlfname,'w')
  if fout.closed:
    logging.error( 'Failed to open output XML file: %s'%(xmlfname))
    easy_exit(-6,[dbcfg,alertdbcfg])
  try:
    root.write(fout,pretty_print=True)
    fout.close()
  except:
    try:
      outtxt = ET.tostring(root)
      fout.write(outtxt)
      fout.close()
    except:
      fout.close()
      logging.error( 'Failed to open output XML file: %s'%(xmlfname))
      easy_exit(-6,[dbcfg,alertdbcfg])

  # Close DB connections
  dbcfg.curs.close()
  dbcfg.dbconn.commit()
  # Remove lock
  easy_exit(0,[dbcfg,alertdbcfg])

