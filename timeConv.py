#!/usr/bin/env python
################################################################################
#  time-conv.py
#  gcn-parser
#
#  Created by Brian Baughman on 2014/04/30.
################################################################################
from numpy import  pi, remainder, floor
from datetime import datetime, time, timedelta


J2000Origin = datetime(2000,1,1,12,0,0,0,None)
J2000JD = 2451545.0
TJD0 = 2440000.5

secInday = 60.*60.*24.

sid2sol = 1.00273790935

def tjd2jd(tjd):
  return tjd + TJD0

def tjd2dttm(tjd):
  return jd2dttm(tjd2jd(tjd))

def jd2dttm(jd):
  tdeldays = jd - J2000JD
  d = floor(tdeldays)
  df = tdeldays - d
  sf = df*secInday
  s = floor(sf)
  msf = 1e6*(sf - s)
  ms = floor(msf)
  tdel = timedelta(d,s,ms)
  return J2000Origin + tdel

def dttm2jd(doi):
  '''
  Returns the Julian day of the the datetime give
  '''
  tdel = doi - J2000Origin
  tdeldays = tdel.days + (tdel.seconds + tdel.microseconds*1e-6)/secInday
  return J2000JD + tdeldays

def dttm2jd0(doi):
  '''
  Returns the Julian day of the preceding midnight in UTC of the datetime give
  '''
  utcdoi = doi.utctimetuple()
  doiutc0 = datetime(utcdoi.tm_year,utcdoi.tm_mon, utcdoi.tm_mday,0,0,0,0,None)
  return dttm2jd(doiutc0)


def dttm2GMST(doi):
  '''
  Given a datetime object of interest returns the
  Greenwich mean sidereal time (GMST) in hours.
  '''
  utcdoi = doi.utctimetuple()
  doiutc0 = datetime(utcdoi.tm_year,utcdoi.tm_mon, utcdoi.tm_mday,0,0,0,0,None)
  JD = dttm2jd(doi)
  JD0 = dttm2jd(doiutc0)
  H = ((doi - doiutc0).total_seconds())/3600.
  D0 = JD0 - J2000JD
  D = JD - J2000JD
  T = D/36525.
  return 6.697374558 + 0.06570982441908*D0 + 1.00273790935*H + 0.000026*T**2


def dttm2LST(doi,lon=0.):
  '''
  Given a datetime object of interest and a longitude returns the
  Local Sidereal Time (LST)
  doi - datetime object of interest
  lon - longitude in radians
  '''
  nrm = 2.*pi
  GMST = dttm2GMST(doi)
  sidOff = 24.*((lon/nrm)*sid2sol)
  return remainder(GMST+sidOff,24.)

def ST2tm(ST):
  '''
  Given an Sidereal time in hours outputs a time object for easy reading
  ST - Sidereal time in hours
  '''
  C = floor(ST/24.)
  R = ST - C*24.
  h = floor(R)
  mf = 60.*(R - h)
  m = floor(mf)
  sf = 60.*(mf - m)
  s = floor(sf)
  msf = 1e6*(sf - s)
  ms = floor(msf)
  return time(int(h),int(m),int(s),int(ms))

def toRads(angle,units='degrees'):
  units = units.lower()
  if units == 'degrees' or units == 'd' or units == 'deg':
    return deg2rad(angle)
  elif units == 'radians' or units == 'radian' or units == 'rad':
    return angle
  elif units == 'hours' or units == 'hour' or units == 'h':
    arr = angle.split(':')
    nspts = len(arr)
    h = float(arr[0])
    m = 0.
    s = 0.
    if nspts > 1:
      m = float(arr[1])
      if nspts > 2:
        s = float(arr[2])
    rval = (s )/60.
    rval = (rval + m)/60.
    rval = (rval + h)/24.
    rval *= 2.*pi
    return rval
  elif units == 'datetime' or units == 'date' or units == 'time':
    rval = (angle.second + angle.microsecond*1e-6)/60.
    rval = (rval + angle.minute)/60.
    rval = (rval + angle.hour)/24.
    rval *= 2.*pi
    return rval
  elif units == 'deghours' or units == 'deghour' or units == 'dh':
    arr = angle.split(':')
    nspts = len(arr)
    d = float(arr[0])
    m = 0.
    s = 0.
    if nspts > 1:
      m = float(arr[1])
      if nspts > 2:
        s = float(arr[2])
    rval = (s )/60.
    rval = (rval + m)/60.
    rval = (rval + d)/360.
    rval *= 2.*pi
    return rval
  else:
    print 'Invalid units given: %s'%units
    return None


