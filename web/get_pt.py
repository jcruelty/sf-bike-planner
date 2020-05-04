#!/usr/bin/python

import cPickle, cgi, cgitb, math, minjson
from bisect import bisect_left, bisect_right
cgitb.enable()

# (12345.670000, 76543.120000) -> '12345.6700,76543.1200'
def ptToStr(pt):
    if type(pt) == str:
        print pt + " is a str!"
        return pt
    return '%.5f,%.5f' % (pt[0], pt[1])

def distance(pt1, pt2):
    if type(pt1) == str:
        pt1 = strToPt(pt1)
    if type(pt2) == str:
        pt2 = strToPt(pt2)
    x1, x2 = pt1[0], pt2[0]
    y1, y2 = pt1[1], pt2[1]
    return math.sqrt(math.pow(abs(x1 - x2), 2) + math.pow(abs(y1 - y2), 2))

def getClosestPoint(pt, ptsXY, ptsYX, ignorePts):
    """
    getClosestPoint(pt, ptsXY, ptsYX, ignorePts, maxDist)

    Returns closest point to pt (excluding pts in ignorePts)
    ptsXY and ptsYX should be sorted lists of points in G, in form (x,y) and (y,x) respectively
    """
            
    ptsInRange = {} # maps each pt within range to its distance from input
    nPts = len(ptsXY)
    maxDist = 9999999.0 # will get reduced by first dist in range
 
    # init X-coord processing
    i = bisect_left(ptsXY, pt)
    j = bisect_right(ptsXY, pt)
    if i == j:
        j += 1

    # find close pts to the left
    if i >= 0 and i < nPts:
        while i >= 0:
            otherPt = ptsXY[i]
            if otherPt not in ignorePts:
                # if we've hit limit of x/y, stop checking
                nCoordDelta = abs(otherPt[0] - pt[0])
                if nCoordDelta > maxDist:
                    #print "Breaking out on %s because abs(%f - %f) = %f which is > %f" % \
                    #          (ptToStr(otherPt), otherPt[0], pt[0], nCoordDelta, maxDist) 
                    break;
                dist = distance(pt, otherPt)
                if dist > 0.0:
                    if dist < maxDist:
                            maxDist = dist
                    if dist <= maxDist:
                        ptsInRange[otherPt] = dist 
            i = i - 1
    else:
        pass
        #print "%s is apparently the leftmost pt of all pts in ptsXY" % ptToStr(pt)

    # find close pts to the right
    if j >= 0 and j < nPts:
        while j < nPts:
            otherPt = ptsXY[j]
            if otherPt not in ignorePts:
                # if we've hit limit of x/y, stop checking
                nCoordDelta = abs(otherPt[0] - pt[0])
                if nCoordDelta > maxDist:
                    #print "Breaking out on %s because abs(%f - %f) = %f which is > %f" % \
                    #          (ptToStr(otherPt), otherPt[0], pt[0], nCoordDelta, maxDist) 
                    break;
                dist = distance(pt, otherPt)
                if dist > 0.0:
                    if dist < maxDist:
                            maxDist = dist
                    if dist <= maxDist:
                        ptsInRange[otherPt] = dist 
            j = j + 1
    else:
        pass
        #print "%s is apparently the rightmost pt of all pts in ptsXY" % ptToStr(pt)

    # init Y-coord processing
    ptYX = (pt[1],pt[0])
    i = bisect_left(ptsYX, ptYX)
    j = bisect_right(ptsYX, ptYX)
    if i == j:
        j += 1

    # find close pts to the bottom
    if i >= 0 and i < nPts:
        while i >= 0:
            otherPtYX = ptsYX[i]
            if otherPtYX not in ignorePts:
                # if we've hit limit of x/y, stop checking
                nCoordDelta = abs(otherPtYX[0] - ptYX[0])
                if nCoordDelta > maxDist:
                    #print "Breaking out on %s because abs(%f - %f) = %f which is > %f" % \
                    #          (ptToStr(otherPt), otherPt[0], pt[0], nCoordDelta, maxDist) 
                    break;
                dist = distance(ptYX, otherPtYX)
                if dist > 0.0:
                    if dist < maxDist:
                            maxDist = dist
                    if dist <= maxDist:
                        otherPtXY = (otherPtYX[1],otherPtYX[0])
                        ptsInRange[otherPtXY] = dist 
            i = i - 1
    else:
        pass
        #print "%s (xy pt %s) is apparently the bottommost pt of all pts in ptsXY" % (ptToStr(ptYX), ptToStr(pt))

    # find close pts to the top
    if j >= 0 and j < nPts:
        while j < nPts:
            otherPtYX = ptsYX[j]
            if otherPtYX not in ignorePts:
                # if we've hit limit of x/y, stop checking
                nCoordDelta = abs(otherPtYX[0] - ptYX[0])
                if nCoordDelta > maxDist:
                    #print "Breaking out on %s because abs(%f - %f) = %f which is > %f" % \
                    #          (ptToStr(otherPt), otherPt[0], pt[0], nCoordDelta, maxDist) 
                    break;
                dist = distance(ptYX, otherPtYX)
                if dist > 0.0:
                    if dist < maxDist:
                            maxDist = dist
                    if dist <= maxDist:
                        otherPtXY = (otherPtYX[1],otherPtYX[0])
                        ptsInRange[otherPtXY] = dist 
            j = j + 1
    else:
        pass
        #print "%s (xy pt %s) is apparently the topmost pt of all pts in ptsXY" % (ptToStr(ptYX), ptToStr(pt))
  
    result = ptsInRange.keys()
    result.sort(lambda x,y: cmp(ptsInRange[x], ptsInRange[y]))
    return result[0]

"""
Do everything
"""

start = end = outputStr = ""
path = None
form = cgi.FieldStorage()
if not ((form.has_key("start")) and (form.has_key("end"))):
    # do some kind of error reporting
    start = '-0.0,0.0'
    end = '0.0,0.0'
else:
    start = form["start"].value
    end = form["end"].value

lonlat = start.split(',')
startPt = (float(lonlat[0]),float(lonlat[1]))
lonlat = end.split(',')
endPt = (float(lonlat[0]),float(lonlat[1]))

f = open('ptsXY.pkl', 'rb')
ptsXY = cPickle.load(f)
f.close()

f = open('ptsYX.pkl', 'rb')
ptsYX = cPickle.load(f)
f.close()

if not (startPt in ptsXY):
    startPt = getClosestPoint(startPt, ptsXY, ptsYX, [])
if not (endPt in ptsXY):
    endPt = getClosestPoint(endPt, ptsXY, ptsYX, [])
  
output = {'method':'get_pt', 'error':False, 'startPt':ptToStr(startPt),'endPt':ptToStr(endPt)}

outputStr = "Content-Type: text/plain\n"    # TODO: use type application/json ?
outputStr += 'Cache-Control: no-store, no-cache,  must-revalidate\n\n'
outputStr += minjson.write(output)
print outputStr
