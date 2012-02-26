import PIL.Image
img = PIL.Image.open('/home/brian/Downloads/puffy.jpg')

import peerplot
peerplot.init('brian', 'localhost', '8080')

import pylab
pylab.imshow(img, origin='lower')

pylab.draw()
