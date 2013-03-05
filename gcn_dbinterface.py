#!/usr/bin/env python
################################################################################
#  gcn_dbinterface.py
#  pyanalysis
#
#  Created by Brian Baughman on 11/9/11.
#  Copyright 2011 Brian Baughman. All rights reserved.
################################################################################
try:
  import sys, re, time
  from sql_interface import *
  from os import environ, _exit
except:
  _exit(-1)
################################################################################
# Configuration options
# Set time
curtime = time.strftime('%Y-%m-%d %H:%M:%S Z',time.gmtime())
# Home directory
homedir = environ['HOME']

# GCN database
try:
  gcnbfname = environ['GCNDB']
except:
  gcnbfname = '%s/gcns.db'%homedir
try:
  gcndbname = environ['GCNDBNAME']
except:
  gcndbname = "gcns"

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
    self.setDBType()


################################################################################
# SQLITE CONFIGURATION
################################################################################
# DB interface formats
gcndbtblck = "SELECT name FROM sqlite_master WHERE type='table' AND name='%s';"%gcndbname

# Get default structure
tmpgcnentry = gcninfo()
gcndbstruct = tmpgcnentry.__dbstruct__
# Connect to DB
try:
  gcndbconn = connect(gcnbfname)
  gcncurs = gcndbconn.cursor()
  gcncurs.execute(gcndbtblck)
  dbtblstate = gcncurs.fetchone()
  if dbtblstate == None:
    dbctbl = GetDBStr(gcndbname,gcndbstruct)
    gcncurs.execute(dbctbl)
    gcndbconn.commit()
except:
  _exit(-4)

# Update strcture if DB is different
gcndbstruct = GetDBStruct(gcncurs,gcndbname)
################################################################################

# Construct check string
#
gcnchkkeys = ["trigid",
                "datestr"]
gcnchkstruct = {}
for cattr in gcnchkkeys:
  gcnchkstruct[cattr] = gcndbstruct[cattr]
gcnckstr = GetCheckStr(gcndbname,gcnchkstruct)

# Construct insert string
gcninststr = GetInsertStr(gcndbname,gcndbstruct)


gcnupkeys = [ "isnotgrb",
              "posunit",
              "ra","dec","error",
              "inten", "intenunit",
              "mesgtype"]
gcnupstruct = {}
for cattr in gcnupkeys:
  gcnupstruct[cattr] = gcndbstruct[cattr]

def UpdateGCN(newEntry,id):
  ustr = "UPDATE %s SET "%(gcndbname)
  first = True
  for cattr in gcnupkeys:
    if first:
      ustr += '%s=\'%s\''%(cattr,newEntry.__getattribute__(cattr))
      first = False
    else:
      ustr += ', %s=\'%s\''%(cattr,newEntry.__getattribute__(cattr))
  ustr += ' WHERE id=%i'%id
  gcncurs.execute(ustr)
  gcndbconn.commit()
  return 0

def AddGCN(newEntry):
  carr = [ newEntry.__getattribute__(cattr) for cattr in gcnchkstruct.keys()]
  ckstr = gcnckstr%tuple(carr)
  gcncurs.execute(ckstr)
  mtchs = gcncurs.fetchall()
  if len(mtchs) == 0:
    carr = [newEntry.__getattribute__(cattr) for cattr in gcndbstruct.keys() ]
    cintstr = gcninststr%tuple(carr)
    gcncurs.execute(cintstr)
    gcndbconn.commit()
    gcncurs.execute("select last_insert_rowid()")
    retval = gcncurs.fetchall()
    njid = retval[0][0]
    return njid, 1
  elif len(mtchs) == 1:
    # update entry
    UpdateGCN(newEntry,mtchs[-1][gcndbstruct['id']['index']])
    return -1*mtchs[-1][gcndbstruct['id']['index']], -1
  return -1, 0
