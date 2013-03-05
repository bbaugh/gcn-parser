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
  import sys, re, time
  from os import environ, remove, path, _exit, makedirs, stat
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
  from gcn_dbinterface import gcncurs, gcndbconn, gcndbname, \
    gcndbstruct, MakeEntry, gcninfo
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
# Site Setup
################################################################################
# HAWC
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



################################################################################
# Useful functions
################################################################################
def easy_exit(eval):
  '''
    Function to clean up before exiting and exiting itself
  '''
  gcndbconn.commit()
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

################################################################################
# Generic Settings
################################################################################
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
  print '%s : GCNHTTP not set!'%curtime
  easy_exit(-2)

# GCNSMTP
try:
  gcnsmtp = environ['GCNSMTP']
except:
  print '%s : GCNSMTP not set!'%curtime
  easy_exit(-2)

# Get web base
try:
  webbase = environ['GCNWEB']
except:
  webbase = '%s/public_html'%homedir

# Define some regexes
hrefre = re.compile("<[^>]*href=([^\ \"'>]+)>")
# Number of recent GCNs to output
try:
  nrecent = int(environ['NOUTGCNS'])
except:
  nrecent = 100


curtime = time.strftime('%Y-%m-%d %H:%M:%S')

clrs = rcParams['axes.color_cycle']

################################################################################
# Setup plot output base
################################################################################
# Output base
plotsbase = '%s/gcns'%webbase
if dircheck(plotsbase) == False:
  print '%s: Cannot write to: %s\n'%(curtime,plotsbase)
  easy_exit(-2)
if dircheck('%s/thumbs'%plotsbase) == False:
  print '%s: Cannot write to: %s/thumbs\n'%(curtime,plotsbase)
  easy_exit(-3)

# Plot file type
ptype = '.png'
def ephemcalcs(site,odir,evttag,curgcninfo):
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
  filestatus = False
  try:
    tfile = open(ofname,'r')
    tfile.close()
    return transient
  except:
    filestatus = True
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
  return transient



# Grab recents
recentstr = "SELECT DISTINCT datestr FROM %s ORDER BY datestr DESC LIMIT %i ;"%(gcndbname,nrecent)
gcncurs.execute(recentstr)
recent = gcncurs.fetchall()

# XML header
root = ET.Element("xml")
root.attrib['version'] = "1.0"
gcns = ET.SubElement(root, "gcns")

idindex = gcndbstruct['id']['index']
sentindex = gcndbstruct['sent']['index']
try:
  for row in recent:
    print row
    qstr = "SELECT * FROM gcns WHERE datestr='%s' ORDER BY error ASC;"%row[0]
    gcncurs.execute(qstr)
    cmtchs = gcncurs.fetchall()
    cmtch = cmtchs[0]
    sentflg = 0
    for m in cmtchs:
      sentflg += m[sentindex]
      if m[idindex] > cmtch[idindex]:
        cmtch = m
    curgcninfo = MakeEntry(cmtch,gcninfo,gcndbstruct)
    # Calculate position at site
    curmis = curgcninfo.inst.lower().replace('/','_')
    evttag = '%s_gcn_%s'%(curmis,curgcninfo.trigid)
    transient = ephemcalcs(site,plotsbase,evttag,curgcninfo)
    if transient.alt > pi*.25 and sentflg == 0:
      try:
        gcnlink = hrefre.findall(curgcninfo.trigid)[0]
        shrturl = shorten(gcnlink)
      except:
        shrturl = ""
      if shrturl != "":
        shrturl = ' %s'%shrturl
        sbjct = sbjctfmt%(curgcninfo.datestr,sitetag.capitalize())
        txt = gettxt(curgcninfo,90.-rad2deg(transient.alt),shrturl)
        ustr = "UPDATE gcns SET sent=1 WHERE trigid='%s';"%curgcninfo.trigid
        try:
          gcncurs.execute(ustr)
          gcndbconn.commit()
          email(sender,recipients,sbjct,txt)
          print '%s: Sent: %s\n'%(curtime,sbjct)
        except:
          print '%s: Failed to send notification or update DB.\n'%(curtime)
    
    # Save to XML
    curgcn = ET.SubElement(gcns, "gcn")
    if transient.alt > site.horizon:
      curgcn.attrib['class'] = "obs"
    else:
      curgcn.attrib['class'] = "outfov"
    for cattr in gcndbstruct.keys():
      cursubelm = ET.SubElement(curgcn,cattr)
      cursubelm.text = str(curgcninfo.__getattribute__(cattr))
    ctalt = rad2deg(transient.alt)
    cursubelm = ET.SubElement(curgcn,'%s_zenith'%sitetag)
    cursubelm.text = str(90.-ctalt)
    cursubelm = ET.SubElement(curgcn,'%s_img'%sitetag)
    ofname = '%s/gcns/%s_%s_altitude_timeline%s'%(gcnhttp,evttag,sitetag.lower(),ptype)
    othbfname = '%s/gcns/thumbs/%s_%s_altitude_timeline_tn%s'%(gcnhttp,evttag,sitetag.lower(),ptype)

    cursubelm.text = '<a href="%s"><img alt="Angry face" src="%s"></a>'%(ofname,othbfname)
except:
  print '%s: Failed while looping over GCNs\n'%(curtime)
  easy_exit(-6)


outtxt = ET.tostring(root)

# Save XML
xmlfname = '%s/gcns.xml'%webbase
fout = open(xmlfname,'w')
if fout.closed:
  print '%s: Failed to open output XML file: %s\n'%(curtime,xmlfname)
  easy_exit(-6)
fout.write(outtxt)
fout.close()

# Close DB connections
gcncurs.close()
gcndbconn.commit()

# Remove lock
easy_exit(0)

