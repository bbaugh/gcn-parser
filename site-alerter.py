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
  from os import environ, path, _exit, makedirs, stat, access, X_OK
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

def ephemcalcs(site,odir,evttag,curgcninfo,toffset,ptype,up):
  '''
    Calculate sky locations and output plot
  '''
  ephemeventtime = ephem.Date(str(curgcninfo.datestr).replace('T',' '))
  eventtime = date2num(ephemeventtime.datetime())
  site.date = ephemeventtime
  rahrs = ephem.hours(deg2rad(float(curgcninfo.ra)))
  dechrs = ephem.degrees(deg2rad(float(curgcninfo.dec)))
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
    transientpositions.append([gt,transient.az,transient.alt,transient.ra,transient.dec])
  
  transientpositions = asarray(transientpositions)
  angerr = float(curgcninfo.error)
  f = figure(num=2,figsize=array([ 8.   ,  6.725]))
  f.clear()
  ax = f.add_subplot(111)
  skplt = ax.plot_date(transientpositions[:,0],rad2deg(transientpositions[:,2]),clrs[0]+'o')
  hghplt = ax.plot_date(transientpositions[:,0],rad2deg(transientpositions[:,2])+angerr,clrs[3]+':')
  lowplt = ax.plot_date(transientpositions[:,0],rad2deg(transientpositions[:,2])-angerr,clrs[3]+':')
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
    gcnbfname = environ['GCNDB']
  except:
    gcnbfname = '%s/gcns.db'%homedir
  try:
    gcndbname = environ['GCNDBNAME']
  except:
    gcndbname = "gcns"
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
                      filemode='a', level=logging.ERROR)
  ##############################################################################
  # Get Database
  ##############################################################################
  if not path.isfile(gcnbfname):
    logging.info('DB file not found: %s'%gcnbfname)
    easy_exit(-1)

  if not access(gcnbfname):
    logging.info('DB inaccessible: %s'%gcnbfname)
    easy_exit(-1)

  dbcfg = GetConfig(gcnbfname,gcndbname)
  ##############################################################################
  # Generic Settings
  ##############################################################################
  # Data base entry format
  dbfmt = "%s,f|V|F7,%s,%s,1,2000"
  # Subject of email format
  sbjctfmt = 'GCN at %s in %s FOV'
  # Content of email format
  txtfmt = '%s trigger %s%s was in the FOV of %s at %.2f degrees from Zenith. More info at %s'

  # Get web base
  try:
    gcnhttp = environ['GCNHTTP']
  except:
    logging.error('GCNHTTP not set!')
    easy_exit(-2)

  # GCNSMTP
  try:
    gcnsmtp = environ['GCNSMTP']
  except:
    logging.error( 'GCNSMTP not set!')
    easy_exit(-2)

  # Get web base
  try:
    gcnweb = environ['GCNWEB']
  except:
    gcnweb = '%s/public_html'%homedir

  # Define some regexes
  hrefre = re.compile("<[^>]*href=([^\ \"'>]+)>")
  # Number of recent GCNs to output
  try:
    nrecent = int(environ['NOUTGCNS'])
  except:
    nrecent = 100

  clrs = rcParams['axes.color_cycle']


  # Plot file type
  ptype = '.png'

  ################################################################################
  # Setup plot output base
  ################################################################################
  # Output base
  plotsbase = '%s/gcns'%gcnweb
  if dircheck(plotsbase) == False:
    logging.error( '%s: Cannot write to: %s\n'%(curtime,plotsbase))
    easy_exit(-2)
  if dircheck('%s/thumbs'%plotsbase) == False:
    logging.error( '%s: Cannot write to: %s/thumbs\n'%(curtime,plotsbase))
    easy_exit(-3)


  ################################################################################
  # Get Database
  ################################################################################
  try:
    dbcfg = GetConfig(gcnbfname,gcndbname)
  except:
    logging.error('Could not read %s'%gcndbname)
    easy_exit(-2)
  ################################################################################
  # Meat
  ################################################################################

  # Grab recents
  recentstr = "SELECT DISTINCT datestr,id FROM %s ORDER BY datestr DESC LIMIT %i ;"%(dbcfg.gcndbname,nrecent)
  dbcfg.gcncurs.execute(recentstr)
  recent = dbcfg.gcncurs.fetchall()

  # XML header
  root = ET.Element("xml")
  root.attrib['version'] = "1.0"
  gcns = ET.SubElement(root, "gcns")

  idindex = dbcfg.gcndbstruct['id']['index']
  sentindex = dbcfg.gcndbstruct['sent']['index']
  updateindex = dbcfg.gcndbstruct['updated']['index']
  for row in recent:
    # Check if this entry has been updated
    print row
    upd = False
    qstr = "SELECT * FROM gcns WHERE id='%s' ORDER BY error ASC;"%row[1]
    dbcfg.gcncurs.execute(qstr)
    cmtchs = dbcfg.gcncurs.fetchall()
    for m in cmtchs:
      if m[updateindex]:
        upd = True
    
    curgcninfo = MakeEntry(cmtchs[0],gcninfo,dbcfg.gcndbstruct)
    # Calculate position at site
    curmis = curgcninfo.inst.lower().replace('/','_')
    evttag = '%s_gcn_%s'%(curmis,curgcninfo.trigid)
    transient,ofname,othbfname = ephemcalcs(site,plotsbase,evttag,curgcninfo,toffset,ptype,upd)
    ustr = "UPDATE gcns SET updated=0 WHERE id='%s';"%row[1]
    try:
      gcncurs.execute(ustr)
      gcndbconn.commit()
    except:
      logging.error( 'Failed to update DB.')

    if transient.alt > pi*.25 and sentflg == 0:
      gcnlink = hrefre.findall(curgcninfo.trigid)[0]
      shrturl = shorten(gcnlink)
      if shrturl != "":
        shrturl = ' %s'%shrturl
        sbjct = sbjctfmt%(curgcninfo.datestr,sitetag.capitalize())
        txt = gettxt(curgcninfo,90.-rad2deg(transient.alt),shrturl)
        ustr = "UPDATE gcns SET sent=1 WHERE trigid='%s';"%curgcninfo.trigid
        try:
          gcncurs.execute(ustr)
          gcndbconn.commit()
          email(sender,recipients,sbjct,txt)
          logging.info( 'Sent: %s'%(sbjct))
        except:
          logging.error( 'Failed to send notification or update DB.')
          continue
    
    # Save to XML
    curgcn = ET.SubElement(gcns, "gcn")
    if transient.alt > site.horizon:
      curgcn.attrib['class'] = "obs"
    else:
      curgcn.attrib['class'] = "outfov"
    for cattr in dbcfg.gcndbstruct.keys():
      cursubelm = ET.SubElement(curgcn,cattr)
      cursubelm.text = str(curgcninfo.__getattribute__(cattr))
    ctalt = rad2deg(transient.alt)
    cursubelm = ET.SubElement(curgcn,'%s_zenith'%sitetag)
    cursubelm.text = str(90.-ctalt)
    cursubelm = ET.SubElement(curgcn,'%s_img'%sitetag)
    cursubelm.text = '<a href="%s"><img alt="Angry face" src="%s"></a>'%(ofname,othbfname)



  outtxt = ET.tostring(root)

  # Save XML
  logging.info( 'Updating XML')
  xmlfname = '%s/gcns.xml'%gcnweb
  fout = open(xmlfname,'w')
  if fout.closed:
    logging.error( 'Failed to open output XML file: %s'%(xmlfname))
    easy_exit(-6)
  fout.write(outtxt)
  fout.close()

  # Close DB connections
  dbcfg.gcncurs.close()
  dbcfg.gcndbconn.commit()
  # Remove lock
  easy_exit(0)

