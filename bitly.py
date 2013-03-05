#!/usr/bin/env python
################################################################################
#  bitly.py
#  pyanalysis
#
#  Created by Brian Baughman on 10/26/11.
#  Copyright 2011 Brian Baughman. All rights reserved.
################################################################################
import sys, re, urllib2
from os import environ

try:
  bitlyapi = environ['BITLYAPI']
except:
  homedir = environ['HOME']
  bitlyapi = '%s/.bitlyapi'%homedir

bitlyre = re.compile('"shortCNAMEUrl":\s*"([^"]+)"')
bitlyfmt = 'http://api.j.mp/shorten?version=2.0.1&longUrl=%s&login=%s&apiKey=%s'

bitlyapif = open(bitlyapi,'r')
busr,bapi = bitlyapif.readlines()
busr = busr.strip()
bapi = bapi.strip()
bitlyapif.close()


def shorten(longurl):
  burl = bitlyfmt%(longurl,busr,bapi)
  response = urllib2.urlopen(burl)
  bitlyraw = response.read()
  response.close()
  try:
    surl = bitlyre.findall(bitlyraw)[0]
    return surl
  except:
    return ""