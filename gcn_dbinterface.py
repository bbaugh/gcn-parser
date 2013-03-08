#!/usr/bin/env python
################################################################################
#  gcn_dbinterface.py
#  pyanalysis
#
#  Created by Brian Baughman on 11/9/11.
#  Copyright 2011 Brian Baughman. All rights reserved.
################################################################################
try:
  import sys, re
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
    self.datestr = "unset"
    self.isnotgrb = "unset"
    self.posunit = "unset"
    self.ra = "unset"
    self.dec = "unset"
    self.error = "unset"
    self.inten = "unset"
    self.intenunit = "unset"
    self.mesgtype = "unset"
    # Derived
    self.sent = 0
    self.inst = "unset"
    self.updated = 0
    self.setDBType()


################################################################################
# SQLITE CONFIGURATION
################################################################################
# Keys to match on 
gcnchkkeys = ["trigid",
              "datestr"]
# Keys to update
gcnupkeys = [ "isnotgrb",
             "posunit",
             "ra","dec","error",
             "inten", "intenunit",
             "mesgtype"]

class gcndbcfg:
  def __init__(self):
    self.gcndbname = None
    self.gcndbtblck = None
    self.gcndbconn = None
    self.gcncurs  = None
    self.gcndbstruct = None
    self.gcnchkstruct = None
    self.gcnckstr = None
    self.gcninststr = None
    self.gcnupstruct = None

def GetConfig(gcnbfname,gcndbname):
  '''
    Returns configuration for given DB
  '''
  rcfg = gcndbcfg()
  rcfg.gcndbname = gcndbname
  # DB interface formats
  rcfg.gcndbtblck = "SELECT name FROM sqlite_master WHERE type='table' AND name='%s';"%rcfg.gcndbname

  # Get default structure
  tmpgcnentry = gcninfo()
  gcndbstruct = tmpgcnentry.__dbstruct__
  # Connect to DB
  try:
    rcfg.gcndbconn = connect(gcnbfname)
    rcfg.gcncurs = rcfg.gcndbconn.cursor()
    rcfg.gcncurs.execute(rcfg.gcndbtblck)
    dbtblstate = rcfg.gcncurs.fetchone()
    if dbtblstate == None:
      dbctbl = GetDBStr(rcfg.gcndbname,gcndbstruct)
      rcfg.gcncurs.execute(dbctbl)
      rcfg.gcndbconn.commit()
  except:
    None

  # Update strcture if DB is different
  rcfg.gcndbstruct = GetDBStruct(rcfg.gcncurs,rcfg.gcndbname)
  ################################################################################

  # Construct check string
  #

  rcfg.gcnchkstruct = {}
  for cattr in gcnchkkeys:
    rcfg.gcnchkstruct[cattr] = rcfg.gcndbstruct[cattr]
  rcfg.gcnckstr = GetCheckStr(rcfg.gcndbname,rcfg.gcnchkstruct)

  # Construct insert string
  rcfg.gcninststr = GetInsertStr(rcfg.gcndbname,rcfg.gcndbstruct)

  rcfg.gcnupstruct = {}
  for cattr in gcnupkeys:
    rcfg.gcnupstruct[cattr] = rcfg.gcndbstruct[cattr]
  return rcfg

def UpdateGCN(newEntry,id,cfg):
  ustr = "UPDATE %s SET updated=1 "%(cfg.gcndbname)
  for cattr in gcnupkeys:
    ustr += ', %s=\'%s\''%(cattr,newEntry.__getattribute__(cattr))
  ustr += ' WHERE id=%i'%id
  cfg.gcncurs.execute(ustr)
  cfg.gcndbconn.commit()
  return 0

def AddGCN(newEntry,cfg):
  carr = [ newEntry.__getattribute__(cattr) for cattr in cfg.gcnchkstruct.keys()]
  ckstr = cfg.gcnckstr%tuple(carr)
  cfg.gcncurs.execute(ckstr)
  mtchs = cfg.gcncurs.fetchall()
  if len(mtchs) == 0:
    carr = [newEntry.__getattribute__(cattr) for cattr in cfg.gcndbstruct.keys() ]
    cintstr = cfg.gcninststr%tuple(carr)
    cfg.gcncurs.execute(cintstr)
    cfg.gcndbconn.commit()
    cfg.gcncurs.execute("select last_insert_rowid()")
    retval = cfg.gcncurs.fetchall()
    njid = retval[0][0]
    return njid, 1
  elif len(mtchs) == 1:
    # update entry
    UpdateGCN(newEntry,mtchs[-1][cfg.gcndbstruct['id']['index']],cfg)
    return -1*mtchs[-1][cfg.gcndbstruct['id']['index']], -1
  return -1, 0
