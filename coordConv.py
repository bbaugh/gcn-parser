#!/usr/bin/env python
################################################################################
#  bitly.py
#  pyanalysis
#
#  Created by Brian Baughman on 10/26/11.
#  Copyright 2011 Brian Baughman. All rights reserved.
################################################################################
from os import environ
from numpy import floor, sin, cos, tan, arcsin, arccos, arctan2, pi, remainder
from timeConv import dttm2LST

def eq2horz(obslat,obslon,doi,RA,dec):
  '''
  Given:
        observer latitude and longitude
        event time
        RA and dec
  returns the Horizontal Geocentric Coordinates.
  All angles given in radians
  obslat - observer latitude
  obslong - observer longitude
  doi - datetime object of interest
  RA - right ascension of event
  dec - declination of event
  '''
  LST = dttm2LST(doi,obslon)
  H = 2.*pi*remainder(LST,24.)/24. - RA
  sinalt = sin(dec)*sin(obslat) + cos(dec)*cos(obslat)*cos(H)
  alt = arcsin(sinalt)
  sinaz = - sin(H)*cos(dec) / cos(alt)
  cosaz = ( sin(dec) - sin(obslat)*sinalt ) / (cos(obslat)*cos(alt))
  az = arctan2(sinaz,cosaz)
  return alt, az

def horz2eq(obslat,obslon,doi,alt,az):
  '''
  Given:
        observer latitude and longitude
        event time
        RA and dec
  returns the Equatorial Coordinates.
  All angles given in radians
  obslat - observer latitude
  obslong - observer longitude
  doi - datetime object of interest
  alt - altitude angle of event
  az - azimuthal angle of event
  '''
  LST = dttm2LST(doi,obslon)
  sindec = sin(alt)*sin(obslat) + cos(alt)*cos(obslat)*cos(az)
  dec = arcsin(sindec)
  cosdec = cos(dec)
  sinHA = - sin(az)*cos(alt) / cosdec
  cosHA = ( sin(alt) - sindec * sin(obslat)) / (cosdec*cos(obslat))
  HA = arctan2(sinHA,cosHA)
  RA = 2.*pi*remainder(LST,24.)/24. - HA
  return RA, dec

