#!/usr/bin/env python
################################################################################
#  sql_interface.py
#  pyanalysis
#
#  Created by Brian Baughman on 11/7/11.
#  Copyright 2011 Brian Baughman. All rights reserved.
################################################################################
import sys, re, time
try:
  from sqlite3 import connect
except:
  try:
    from sqlite import connect
  except:
    sys.exit(-2)
from os import environ, access

attrre = re.compile("^_(.*?)_$")
datere = re.compile("_date$")

class baseentry(object):
  def __init__(self):
    self.id = "null" # This is a special name and WILL be the primary key
    self.__dbkeys__ = []
    self.__dbstruct__ = None
  def setDBType(self):
    self.__dbkeys__ = []
    self.__dbstruct__ = {}
    cindx = 0
    for cattr in sorted(self.__dict__):
      cmatches = attrre.findall(cattr)
      if len(cmatches)>0:
        continue
      ctype = type(self.__getattribute__(cattr))
      cnulstat = "NOT NULL"
      cfmt = "'%s'"
      cdbtype = "BLOB"
      if cattr=="id":
        cnulstat = ""
        cfmt = "%s"
        cdbtype = "INTEGER PRIMARY KEY"
      elif len(datere.findall(cattr))>0:
        cdbtype = "DATETIME"      
      elif ctype == str or ctype == unicode:
        cdbtype = "TEXT"
      elif ctype == float :
        cfmt = "%g"
        cdbtype = "REAL"
      elif ctype == int or ctype == long:
        cfmt = "%i"
        cdbtype = "INTEGER"
      self.__dbkeys__.append(cattr)
      self.__dbstruct__[cattr] = { "type":ctype, "dbtype":cdbtype, "fmt":cfmt,
                                   "index":cindx, "nulstat" : cnulstat }
      cindx += 1


def GetDBStruct(dbcur,dbname):
  dbcur.execute("PRAGMA table_info(%s)"%dbname)
  tblinfo = dbcur.fetchall()
  dbstruct = {}
  for col in tblinfo:
    cattr = col[1]
    cnulstat = "NOT NULL"
    cfmt = "'%s'"
    cdbtype = col[2]
    cindx = col[0]
    if cattr=="id":
      ctype = int
      cnulstat = ""
      cfmt = "%s"
      cdbtype = "%s PRIMARY KEY"%col[2]
    elif cdbtype == "DATETIME":
      ctype = str      
    elif cdbtype == "TEXT":
      ctype = unicode
    elif cdbtype == "REAL":
      cfmt = "%g"
      ctype = float
    elif cdbtype == "INTEGER":
      cfmt = "%i"
      ctype = int
    dbstruct[cattr] = { "type":ctype, "dbtype":cdbtype, "fmt":cfmt,
      "index":cindx, "nulstat" : cnulstat }
  return dbstruct


def GetDBStr(dbname,dbstruct):
  dbctbl = "CREATE TABLE %s ("%dbname
  carr = ["" for i in xrange(len(dbstruct.keys()))]
  for cattr in dbstruct.keys():
    cdbtype = dbstruct[cattr]['dbtype']
    cnulstat = dbstruct[cattr]['nulstat']
    carr[dbstruct[cattr]['index']] = "%s %s %s"%(cattr,cdbtype,cnulstat)
  return "%s%s);"%(dbctbl,','.join(carr))

def GetInsertStr(dbname,dbstruct):
  carr = []
  cattrarr = []
  for cattr in dbstruct.keys():
    cattrarr.append(cattr)
    carr.append(dbstruct[cattr]['fmt'])
  return "INSERT INTO %s (%s) VALUES (%s);"%(dbname,
                                             ','.join(cattrarr),
                                             ','.join(carr))

def GetCheckStr(dbname,dbstruct):
  carr = []
  for cattr in dbstruct.keys():
    if cattr == "id":
      continue
    carr.append("%s=%s"%(cattr,dbstruct[cattr]['fmt']))
  return unicode("SELECT * FROM %s WHERE %s;"%(dbname,' and '.join(carr)))

def Check(curs,dbname,curEntry):
  carr = []
  for cattr in curEntry.__dbkeys__:
    if cattr == "id":
      continue
    carr.append(curEntry.__getattribute__(cattr))
  chkstr = GetCheckStr(dbname,curEntry.__dbstruct__)%tuple(carr)
  curs.execute(newchk)
  rply = curs.fetchall()
  return len(rply)

def UpdateDB(curs,dbname,curEntry):
  if Check(curs,dbname,curEntry) == 0:
    carr = [curEntry.__getattribute__(cattr) for cattr in curEntry.__dbkeys__ ]
    newent = GetInsertStr(dbname,curEntry.__dbstruct__)%tuple(carr)
    curs.execute(newent)
    return

def MakeEntry(dbrow,entry,dbstruct):
  newEntry = entry()
  for cattr in dbstruct.keys():
    newEntry.__setattr__(cattr,dbrow[dbstruct[cattr]['index']])
  newEntry.__dbstruct__ = dbstruct
  newEntry.__dbkeys__ = dbstruct.keys()
  return newEntry

def CheckDB(dbcurs,dbname,dbstruct):
  dbtblchk = "SELECT name FROM sqlite_master WHERE type='table' AND name='%s';"%dbname
  try:
    dbcurs.execute(dbtblchk)
    dbtblstate = dbcurs.fetchone()
    if dbtblstate == None:
      dbctbl = GetDBStr(dbname,dbstruct)
      dbcurs.execute(dbctbl)
      dbcurs.connection.commit()
  except:
    return None
  return GetDBStruct(dbcurs,dbname)

