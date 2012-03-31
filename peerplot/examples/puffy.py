import PIL.Image
img = PIL.Image.open('/home/brian/Downloads/puffy.jpg')

import peerplot
peerplot.init('RodH42')

import pylab
pylab.imshow(img, origin='lower')

pylab.draw()
