#!/usr/bin/env python
################################################################################
#  bitly.py
#  pyanalysis
#
#  Created by Brian Baughman on 10/26/11.
#  Copyright 2011 Brian Baughman. All rights reserved.
################################################################################
from os import environ
from time import sleep

try:
  bitlyapi = environ['BITLYAPI']
except:
  homedir = environ['HOME']
  bitlyapi = '%s/.bitlyapi'%homedir

try:
  import re, urllib2
  bitlyre = re.compile('"shortCNAMEUrl":\s*"([^"]+)"')
  bitlyfmt = 'http://api.j.mp/shorten?version=2.0.1&longUrl=%s&login=%s&apiKey=%s'

  bitlyapif = open(bitlyapi,'r')
  busr,bapi = bitlyapif.readlines()
  busr = busr.strip()
  bapi = bapi.strip()
  bitlyapif.close()
  
  def shorten(longurl):
    '''
      Shortens URLs using bitly's service
      If an error occurs contacting bitly it will try a total of 5 times waiting
      5 seconds between each
    '''
    burl = bitlyfmt%(longurl,busr,bapi)
    for i in xrange(5):
      bitlyraw = None
      try:
        response = urllib2.urlopen(burl)
        bitlyraw = response.read()
        response.close()
        break
      except:
        sleep(5)
    try:
      surl = bitlyre.findall(bitlyraw)[0]
      return surl
    except:
      return longurl
except:
  '''
    If bitly cannot be loaded do not shorten URLs
  '''
  def shorten(longurl):
    return longurl