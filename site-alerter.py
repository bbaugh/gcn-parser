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
  import matplotlib
  matplotlib.use('agg')
  from matplotlib import dates as mpldates
  from matplotlib.cbook import is_numlike
  from matplotlib import rcParams
  from matplotlib.pyplot import draw, figure
  from matplotlib.dates import datestr2num,date2num
  import matplotlib.image as image
  from numpy import deg2rad, rad2deg, arange, asarray, array, pi, where,\
    iterable
  import ephem
  from bitly import shorten

  # Home directory
  homedir = environ['HOME']
  # stop if something looks wrong
except:
  print 'Failed to load modules'
  _exit(-1)

##############################################################################
# Generic Settings
##############################################################################
# Data base entry format
dbfmt = "%s,f|V|F7,%s,%s,1,2000"
# Subject of email format
sbjctfmt = 'GCN at %s in %s FOV'
# Content of email format
txtfmt = '%s trigger %s was in the FOV of %s at %.2f degrees from Zenith. More info at %s and %s'
# Define some regexes
hrefre = re.compile("<[^>]*href=([^\ \"'>]+)>")
# Easy access to colors
clrs = rcParams['axes.color_cycle']
# Plot file type
ptype = '.png'

################################################################################
# Define DB structure
################################################################################
class alertinfo(baseentry):
  def __init__(self):
    self.id = "null"
    # Read directly
    self.trigid = "unset"
    self.trig_date = "unset"
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
                cinfo.link,\
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

def ephemcalcs(site,odir,evttag,curinfo,toffset,ptype,up):
  '''
    Calculate sky locations and output plot
  '''
  ephemeventtime = ephem.Date(str(curinfo.trig_date).replace('T',' '))
  eventtime = date2num(ephemeventtime.datetime())
  site.date = ephemeventtime
  rahrs = ephem.hours(deg2rad(float(curinfo.ra)))
  dechrs = ephem.degrees(deg2rad(float(curinfo.dec)))
  # Load source into ephem
  line = dbfmt%(evttag.replace(',','_'),rahrs,dechrs)
  transient = ephem.readdb(line)
  transient.compute(site)
  # Check we want to plt
  ofname = '%s/%s_%s_altitude_timeline%s'%(odir,evttag,sitetag.lower(),ptype)
  othbfname = '%s/thumbs/%s_%s_altitude_timeline_tn%s'%(odir,evttag,sitetag.lower(),ptype)
  if not upd:
    return transient,ofname,othbfname

  # Plot the data
  startdate = eventtime - .5
  enddate = eventtime + .5
  
  site.date = ephem.Date(startdate)
  mdates = arange(startdate,enddate,1./(24.*4))
  
  transientpositions = []
  for gt in mdates:
    site.date = gt - toffset
    transient.compute(site)
    transientpositions.append([gt,\
                               transient.az,transient.alt,\
                               transient.ra,transient.dec])
  
  transientpositions = asarray(transientpositions)
  angerr = float(curinfo.error)
  f = figure(num=2,figsize=array([ 8.   ,  6.725]))
  f.clear()
  ax = f.add_subplot(111)
  skplt = ax.plot_date(transientpositions[:,0],\
                       rad2deg(transientpositions[:,2]),clrs[0]+'o')
  hghplt = ax.plot_date(transientpositions[:,0],\
                        rad2deg(transientpositions[:,2])+angerr,clrs[3]+':')
  lowplt = ax.plot_date(transientpositions[:,0],\
                        rad2deg(transientpositions[:,2])-angerr,clrs[3]+':')
  ax.xaxis.set_major_formatter(mpldates.DateFormatter('%m/%d %H:%M'))
  ylms = ax.get_ylim()
  evtplt = ax.plot_date([eventtime,eventtime],[-90,90],clrs[1]+'--')
  ax.set_xlabel('Date [UTC]')
  ax.set_ylabel('Altitude Angle [degrees]')
  ax.set_title('GCN: %s'%(evttag))
  ax.set_ylim(0,90.5)
  ax.grid()
  f.autofmt_xdate()
  draw()
  f.savefig(ofname)
  # Save a thumbnail of the plot
  fig = image.thumbnail(str(ofname), str(othbfname), scale=0.1)
  site.date = ephemeventtime
  transient.compute(site)
  return transient,ofname,othbfname

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
  site = ephem.Observer()
  try:
    sitetag = environ['GCNSITE']
  except:
    sitetag = 'HAWC'
  try:
    site.lat = environ['GCNSITELAT']
  except:
    site.lat = "+19.0304954539937"
  try:
    site.long = environ['GCNSITELONG']
  except:
    site.long = "-97.2698484177274"
  try:
    site.horizon = environ['GCNSITEHORIZON']
  except:
    site.horizon = "45.000"

  # Time Offsets
  ephemnow = ephem.now()
  now = date2num(ephemnow.datetime())
  toffset = now - ephemnow

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
  # Setup plot output base
  ################################################################################
  # Output base
  plotsbase = '%s/gcns'%gcnweb
  if dircheck(plotsbase) == False:
    logging.error( 'Cannot write to: %s'%(plotsbase))
    easy_exit(-2,[dbcfg,alertdbcfg])
  if dircheck('%s/thumbs'%plotsbase) == False:
    logging.error( 'Cannot write to: %s/thumbs'%(plotsbase))
    easy_exit(-3,[dbcfg,alertdbcfg])

  ################################################################################
  # Meat
  ################################################################################

  # Grab recents
  trig_date = 0
  id = 1
  trigid = 2
  updated_date = 3
  recentstr = "SELECT DISTINCT trig_date,id,trigid,updated_date"
  recentstr += " FROM %s ORDER BY trig_date DESC LIMIT %i ;"%(dbcfg.dbname,\
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
    qstr = "SELECT * FROM %s WHERE trig_date='%s' AND trigid='%s';"
    qstr = qstr%(alertdbcfg.dbname,row[trig_date],row[trigid])
    alertdbcfg.curs.execute(qstr)
    camtchs = alertdbcfg.curs.fetchall()
    if  len(camtchs) == 0:
      ''' 
        Add new entry
      '''
      nAlert = alertinfo()
      nAlert.trigid = row[trigid]
      nAlert.trig_date = row[trig_date]
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
      logging.info('Found multiple entries for %s'%row[trig_date])
      continue
    rEUD = ephem.Date(str(row[updated_date]).replace('T',' '))
    rUD = date2num(rEUD.datetime())
    for m in camtchs:
      mEUD = ephem.Date(str(m[a_updated_date]).replace('T',' '))
      mUD = date2num(mEUD.datetime())
      if rUD > mUD:
        upd = True
      sentflg += m[a_sent]
    
    # Calculate position at site
    qstr = "SELECT * FROM %s WHERE id=%s;"%(dbcfg.dbname,row[id])
    dbcfg.curs.execute(qstr)
    cmtchs = dbcfg.curs.fetchall()
    curinfo = MakeEntry(cmtchs[0],gcninfo,dbcfg.dbstruct)
    curinst = curinfo.inst.lower().replace('/','_')
    evttag = '%s_gcn_%s'%(curinst,curinfo.trigid)
    transient,ofname,othbfname = ephemcalcs(site,plotsbase,evttag,curinfo,\
                                            toffset,ptype,upd)
    if upd:
      logging.debug("Updated %s"%(curinfo.trig_date))
      ustr = "UPDATE %s SET updated_date='%s' WHERE id='%s';"
      ustr = ustr%(alertdbcfg.dbname, row[updated_date], camtchs[0][a_id])
      try:
        alertdbcfg.curs.execute(ustr)
        alertdbcfg.dbconn.commit()
      except:
        logging.error( 'Failed to update Alert DB.')

    if transient.alt > pi*.25 and sentflg == 0:
      sbjct = sbjctfmt%(curinfo.trig_date,sitetag.capitalize())
      txt = gettxt(curinfo,90.-rad2deg(transient.alt),sitetag,sitelink)
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

    # Save to XML
    curgcn = ET.SubElement(gcns, "gcn")
    if transient.alt > site.horizon:
      curgcn.attrib['class'] = "obs"
    else:
      curgcn.attrib['class'] = "outfov"

    for cattr in dbcfg.dbstruct.keys():
      cursubelm = ET.SubElement(curgcn,cattr)
      cursubelm.text = str(curinfo.__getattribute__(cattr))
    ctalt = rad2deg(transient.alt)
    cursubelm = ET.SubElement(curgcn,'%s_zenith'%sitetag)
    cursubelm.text = str(90.-ctalt)
    cursubelm = ET.SubElement(curgcn,'%s_img'%sitetag)
    cursubelm.text = '<a href="%s"><img alt="Angry face" src="%s"></a>'%(ofname,othbfname)




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

