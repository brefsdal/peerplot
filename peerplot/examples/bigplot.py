#!/usr/bin/env python

import time
import sys
import matplotlib
matplotlib.use('module://mplh5canvas.backend_h5canvas')
# matplotlib.use('module://peerplot.backend_h5canvas')
# import peerplot.backend_h5canvas
# peerplot.backend_h5canvas.SESSION_ID = 'brian'

#matplotlib.interactive(True)
import matplotlib.cm as cm
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
import numpy

def plot(X, Y):
    plt.clf()
    tt = time.time()
    plt.plot(X, Y, 'ro')
    plt.draw()
    print 'plot rendered in %g secs' % (time.time()-tt)


x = numpy.linspace(0, 10, 10)
y = x*x

plot(x,y)


# 1,000 points
# opening websocket ...
# Render took 1.85981106758 s
# Path time: 0.00596880912781, Text time: 0.000787973403931, Marker time: 1.83165884018, Sub time: 0.00460243225098
# sending frame....
# Overall draw took 3.2351539135 s, with 0 clipcount
# plot rendered in 3.25309 secs

# 5,000 points
# opening websocket ...
# Render took 49.1449229717 s
# Path time: 0.0347540378571, Text time: 0.00493597984314, Marker time: 49.0350449085, Sub time: 0.0333981513977
# sending frame....
# Overall draw took 56.0012340546 s, with 0 clipcount
# plot rendered in 56.0193 secs

# 10,000 points
# opening websocket ...
# Render took 202.932790041 s
# Path time: 0.068913936615, Text time: 0.00885796546936, Marker time: 202.727214336, Sub time: 0.0601825714111
# sending frame....
# Overall draw took 218.513327122 s, with 0 clipcount
