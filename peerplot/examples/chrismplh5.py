#!/usr/bin/env python

import matplotlib
matplotlib.use('module://peerplot.backend_h5canvas')

import peerplot.backend_h5canvas
peerplot.backend_h5canvas.SESSION_ID = 'chris'

matplotlib.interactive(True)
import matplotlib.cm as cm
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
import numpy

delta = 0.025
x = y = numpy.arange(-3.0, 3.0, delta)
X, Y = numpy.meshgrid(x, y)
Z1 = mlab.bivariate_normal(X, Y, 1.0, 1.0, 0.0, 0.0)
Z2 = mlab.bivariate_normal(X, Y, 1.5, 0.5, 1, 1)
Z = Z2-Z1  # difference of Gaussians

# Create a matplotlib AxesImage object
img = plt.imshow(Z, interpolation='bilinear', cmap=cm.ocean_r, origin='lower', extent=[-3,3,-3,3])
