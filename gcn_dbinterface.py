#!/usr/bin/env python
################################################################################
#  gcn_dbinterface.py
#  pyanalysis
#
#  Created by Brian Baughman on 11/9/11.
#  Copyright 2011 Brian Baughman. All rights reserved.
################################################################################
try:
  import sys, re, datetime
  from sql_interface import *
  from os import environ, _exit
except:
  _exit(-1)


################################################################################
# Class used for storing GCNs with default values.
################################################################################
class gcninfo(baseentry):
  def __init__(self):
    self.id = "null"
    # Read directly
    self.trigid = "unset"
    self.trig_date = "unset"
    self.updated_date = "unset"
    self.isnotgrb = "unset"
    self.posunit = "unset"
    self.ra = "unset"
    self.dec = "unset"
    self.error = "unset"
    self.inten = "unset"
    self.intenunit = "unset"
    self.mesgtype = "unset"
    # Derived
    self.inst = "unset"
    self.link = "unset"
    self.setDBType()


################################################################################
# SQLITE CONFIGURATION
################################################################################
# Keys to match on 
gcnchkkeys = ["trigid",
              "trig_date"]
# Keys to update
gcnupkeys = [ "isnotgrb",
             "posunit",
             "ra","dec","error",
             "inten", "intenunit",
             "mesgtype"]

def GetGCNConfig(dbfname,dbname):
  return GetConfig(dbfname,dbname,gcninfo,gcnupkeys,gcnchkkeys)

def UpdateGCN(newEntry,id,cfg):
  ustr = "UPDATE %s SET updated_date='%s' "%(cfg.dbname,newEntry.updated_date)
  for cattr in gcnupkeys:
    ustr += ', %s=\'%s\''%(cattr,newEntry.__getattribute__(cattr))
  ustr += ' WHERE id=%i'%id
  cfg.curs.execute(ustr)
  cfg.dbconn.commit()
  return 0

def AddGCN(newEntry,cfg):
  carr = [ newEntry.__getattribute__(cattr) for cattr in cfg.chkstruct.keys()]
  ckstr = cfg.ckstr%tuple(carr)
  cfg.curs.execute(ckstr)
  mtchs = cfg.curs.fetchall()
  if len(mtchs) == 0:
    carr = [newEntry.__getattribute__(cattr) for cattr in cfg.dbstruct.keys() ]
    cintstr = cfg.inststr%tuple(carr)
    cfg.curs.execute(cintstr)
    cfg.dbconn.commit()
    cfg.curs.execute("select last_insert_rowid()")
    retval = cfg.curs.fetchall()
    njid = retval[0][0]
    print "Adding %s (%s)"%(newEntry.trig_date,newEntry.updated_date)
    return njid, 1
  elif len(mtchs) == 1:
    # update entry if newer than already logged
    oldEntry = MakeEntry(mtchs[0],gcninfo,cfg.dbstruct)
    oT = str(oldEntry.updated_date).replace('T',' ')
    oTo = datetime.datetime.strptime(oT,'%Y-%m-%d %H:%M:%S')
    nT = str(newEntry.updated_date).replace('T',' ')
    nTo = datetime.datetime.strptime(nT,'%Y-%m-%d %H:%M:%S')
    dT = (nTo - oTo)
    if dT > datetime.timedelta(seconds = 0):
      UpdateGCN(newEntry,mtchs[0][cfg.dbstruct['id']['index']],cfg)
      print "Updating %s (%s - %s = %i)"%(newEntry.trig_date,newEntry.updated_date,oldEntry.updated_date, dT.total_seconds())
    else:
      print "NOT Updating %s (%s - %s = %i)"%(newEntry.trig_date,newEntry.updated_date,oldEntry.updated_date,dT.total_seconds())
    return -1*mtchs[-1][cfg.dbstruct['id']['index']], -1
  return -1, 0
