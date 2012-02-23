#!/usr/bin/env python
"""
An HTML5 Canvas backend for matplotlib.

Simon Ratcliffe (sratcliffe@ska.ac.za)
Ludwig Schwardt (ludwig@ska.ac.za)

Copyright (c) 2010-2011, SKA South Africa
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
Neither the name of SKA South Africa nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from __future__ import division

import sys
import math
import time
import uuid
import numpy as np

from matplotlib.backend_bases import RendererBase, GraphicsContextBase
from matplotlib.transforms import Affine2D
from matplotlib.path import Path
from matplotlib.colors import colorConverter, rgb2hex
from matplotlib.cbook import maxdict
from matplotlib.ft2font import FT2Font, LOAD_NO_HINTING
from matplotlib.font_manager import findfont
from matplotlib.mathtext import MathTextParser
from matplotlib import _png


__all__ = ('WebPNG', 'GraphicsContextH5Canvas', 'RendererH5Canvas')


_capstyle_d = {'projecting' : 'square', 'butt' : 'butt', 'round': 'round',}
 # mapping from matplotlib style line caps to H5 canvas


def mpl_to_css_color(color, alpha=None, isRGB=True):
    """Convert Matplotlib color spec (or rgb tuple + alpha) to CSS color string."""
    if not isRGB:
        r, g, b, alpha = colorConverter.to_rgba(color)
        color = (r, g, b)
    if alpha is None and len(color) == 4:
        alpha = color[3]
    if alpha is None:
        return rgb2hex(color[:3])
    else:
        return 'rgba(%d, %d, %d, %.3g)' % (color[0] * 255, color[1] * 255, color[2] * 255, alpha)


class WebPNG(object):
    """Very simple file like object for use with the write_png method.
    Used to grab the output that would have headed to a standard file, and allow further manipulation
    such as base 64 encoding."""
    def __init__(self):
        self.buffer = ""
    def write(self, s):
        self.buffer += s
    def get_b64(self):
        import base64
        return base64.b64encode(self.buffer)


class GraphicsContextH5Canvas(GraphicsContextBase):
    """
    The graphics context provides the color, line styles, etc...  See the gtk
    and postscript backends for examples of mapping the graphics context
    attributes (cap styles, join styles, line widths, colors) to a particular
    backend.  In GTK this is done by wrapping a gtk.gdk.GC object and
    forwarding the appropriate calls to it using a dictionary mapping styles
    to gdk constants.  In Postscript, all the work is done by the renderer,
    mapping line styles to postscript calls.

    If it's more appropriate to do the mapping at the renderer level (as in
    the postscript backend), you don't need to override any of the GC methods.
    If it's more appropriate to wrap an instance (as in the GTK backend) and
    do the mapping here, you'll need to override several of the setter
    methods.

    The base GraphicsContext stores colors as a RGB tuple on the unit
    interval, eg, (0.5, 0.0, 1.0). You may need to map this to colors
    appropriate for your backend.
    """
    pass


class RendererH5Canvas(RendererBase):
    """The renderer handles drawing/rendering operations."""
    fontd = maxdict(50)

    def __init__(self, width, height, ctx, dpi=72):
        self.width = width
        self.height = height
        self.dpi = dpi
        #print "Canvas Width:",width,",Height:",height,",DPI:",dpi
        self.ctx = ctx
        self._image_count = 0
         # used to uniquely label each image created in this figure...
         # define the js context
        self.ctx.width = width
        self.ctx.height = height
        #self.ctx.textAlign = "center";
        self.ctx.textBaseline = "alphabetic"
        self.flip = Affine2D().scale(1, -1).translate(0, height)
        self.mathtext_parser = MathTextParser('bitmap')
        self._path_time = 0
        self._text_time = 0
        self._marker_time = 0
        self._sub_time = 0
        self._last_clip = None
        self._last_clip_path = None
        self._clip_count = 0

    def _set_style(self, gc, rgbFace=None):
        ctx = self.ctx
        if rgbFace is not None:
            ctx.fillStyle = mpl_to_css_color(rgbFace, gc.get_alpha())
        ctx.strokeStyle = mpl_to_css_color(gc.get_rgb(), gc.get_alpha())
        if gc.get_capstyle():
            ctx.lineCap = _capstyle_d[gc.get_capstyle()]
        ctx.lineWidth = self.points_to_pixels(gc.get_linewidth())

    def _path_to_h5(self, ctx, path, transform, clip=None, stroke=True, dashes=(None, None)):
        """Iterate over a path and produce h5 drawing directives."""
        transform = transform + self.flip
        ctx.beginPath()
        current_point = None
        dash_offset, dash_pattern = dashes
        if dash_pattern is not None:
            dash_offset = self.points_to_pixels(dash_offset)
            dash_pattern = tuple([self.points_to_pixels(dash) for dash in dash_pattern])
        for points, code in path.iter_segments(transform, clip=clip):
            # Shift all points by half a pixel, so that integer coordinates are aligned with pixel centers instead of edges
            # This prevents lines that are one pixel wide and aligned with the pixel grid from being rendered as a two-pixel wide line
            # This happens because HTML Canvas defines (0, 0) as the *top left* of a pixel instead of the center,
            # which causes all integer-valued coordinates to fall exactly between pixels
            points += 0.5
            if code == Path.MOVETO:
                ctx.moveTo(points[0], points[1])
                current_point = (points[0], points[1])
            elif code == Path.LINETO:
                t = time.time()
                if (dash_pattern is None) or (current_point is None):
                    ctx.lineTo(points[0], points[1])
                else:
                    dash_offset = ctx.dashedLine(current_point[0], current_point[1], points[0], points[1], (dash_offset, dash_pattern))
                self._sub_time += time.time() - t
                current_point = (points[0], points[1])
            elif code == Path.CURVE3:
                ctx.quadraticCurveTo(*points)
                current_point = (points[2], points[3])
            elif code == Path.CURVE4:
                ctx.bezierCurveTo(*points)
                current_point = (points[4], points[5])
            else:
                pass
        if stroke: ctx.stroke()

    def _do_path_clip(self, ctx, clip):
        self._clip_count += 1
        ctx.save()
        ctx.beginPath()
        ctx.moveTo(clip[0],clip[1])
        ctx.lineTo(clip[2],clip[1])
        ctx.lineTo(clip[2],clip[3])
        ctx.lineTo(clip[0],clip[3])
        ctx.clip()

    def draw_path(self, gc, path, transform, rgbFace=None):
        t = time.time()
        self._set_style(gc, rgbFace)
        clip = self._get_gc_clip_svg(gc)
        clippath, cliptrans = gc.get_clip_path()
        ctx = self.ctx
        if clippath is not None and self._last_clip_path != clippath:
            ctx.restore()
            ctx.save()
            self._path_to_h5(ctx, clippath, cliptrans, None, stroke=False)
            ctx.clip()
            self._last_clip_path = clippath
        if self._last_clip != clip and clip is not None and clippath is None:
            ctx.restore()
            self._do_path_clip(ctx, clip)
            self._last_clip = clip
        if clip is None and clippath is None and (self._last_clip is not None or self._last_clip_path is not None): self._reset_clip()
        if rgbFace is None and gc.get_hatch() is None:
            figure_clip = (0, 0, self.width, self.height)
        else:
            figure_clip = None
        self._path_to_h5(ctx, path, transform, figure_clip, dashes=gc.get_dashes())
        if rgbFace is not None:
            ctx.fill()
            ctx.fillStyle = '#000000'
        self._path_time += time.time() - t

    def _get_gc_clip_svg(self, gc):
        cliprect = gc.get_clip_rectangle()
        if cliprect is not None:
            x, y, w, h = cliprect.bounds
            y = self.height-(y+h)
            return (x,y,x+w,y+h)
        return None

    def draw_markers(self, gc, marker_path, marker_trans, path, trans, rgbFace=None):
    #    print "Draw markers called: marker_path=",marker_path,",marker_trans=",marker_trans,",path=",path,",trans=",trans
        t = time.time()
        for vertices, codes in path.iter_segments(trans, simplify=False):
            if len(vertices):
                x,y = vertices[-2:]
                self._set_style(gc, rgbFace)
                clip = self._get_gc_clip_svg(gc)
                ctx = self.ctx
                self._path_to_h5(ctx, marker_path, marker_trans + Affine2D().translate(x, y), clip)
                if rgbFace is not None:
                    ctx.fill()
                    ctx.fillStyle = '#000000'
        self._marker_time += time.time() - t

    def _slipstream_png(self, x, y, im_buffer, width, height):
        """Insert image directly into HTML canvas as base64-encoded PNG."""
        # Shift x, y (top left corner) to the nearest CSS pixel edge, to prevent resampling and consequent image blurring
        x = math.floor(x + 0.5)
        y = math.floor(y + 1.5)
        # Write the image into a WebPNG object
        f = WebPNG()
        _png.write_png(im_buffer, width, height, f)
        # Write test PNG as file as well
        #_png.write_png(im_buffer, width, height, 'canvas_image_%d.png' % (self._image_count,))
        # Extract the base64-encoded PNG and send it to the canvas
        uname = str(uuid.uuid1()).replace("-","") #self.ctx._context_name + str(self._image_count)
         # try to use a unique image name

        enc = "var canvas_image_%s = 'data:image/png;base64,%s';" % (uname, f.get_b64())
        s = "function imageLoaded_%s(ev) {\nim = ev.target;\nim_left_to_load_%s -=1;\nif (im_left_to_load_%s == 0) frame_body_%s();\n}\ncanv_im_%s = new Image();\ncanv_im_%s.onload = imageLoaded_%s;\ncanv_im_%s.src = canvas_image_%s;\n" % \
            (uname, self.ctx._context_name, self.ctx._context_name, self.ctx._context_name, uname, uname, uname, uname, uname)
        self.ctx.add_header(enc)
        self.ctx.add_header(s)
        # Once the base64 encoded image has been received, draw it into the canvas
        self.ctx.write("%s.drawImage(canv_im_%s, %g, %g, %g, %g);" % (self.ctx._context_name, uname, x, y, width, height))
         # draw the image as loaded into canv_im_%d...
        self._image_count += 1
        #print "Placed image with w=%g h=%g at x=%g y=%g" % (width, height, x, y)

    def _reset_clip(self):
        self.ctx.restore()
        self._last_clip = None
        self._last_clip_path = None

    #def draw_image(self, gc, x, y, im, clippath=None, clippath_trans=None):
    #<1.0.0: def draw_image(self, x, y, im, bbox, clippath=None, clippath_trans=None):
    #1.0.0 and up: def draw_image(self, gc, x, y, im, clippath=None):
    #API for draw image changed between 0.99 and 1.0.0
    def draw_image(self, *args, **kwargs):
        x, y, im = args[:3]
        try:
            h,w = im.get_size_out()
        except AttributeError:
            x, y, im = args[1:4]
            h,w = im.get_size_out()
        clippath = (kwargs.has_key('clippath') and kwargs['clippath'] or None)
        if self._last_clip is not None or self._last_clip_path is not None: self._reset_clip()
        #h,w = im.get_size_out()
        if clippath is not None:
            self._path_to_h5(self.ctx,clippath, clippath_trans, stroke=False)
            self.ctx.save()
            self.ctx.clip()
        (x,y) = self.flip.transform((x,y))
        im.flipud_out()
        rows, cols, im_buffer = im.as_rgba_str()
        self._slipstream_png(x, (y-h), im_buffer, cols, rows)
        if clippath is not None:
            self.ctx.restore()

    def _get_font(self, prop):
        key = hash(prop)
        font = self.fontd.get(key)
        if font is None:
            fname = findfont(prop)
            font = self.fontd.get(fname)
            if font is None:
                #print "Using font",str(fname)
                #print type(prop)
                font = FT2Font(str(fname))
                self.fontd[fname] = font
            self.fontd[key] = font
        font.clear()
        font.set_size(prop.get_size_in_points(), self.dpi)
        return font

    def draw_tex(self, gc, x, y, s, prop, angle, ismath=False):
        print "Tex support is currently not implemented. Text element '",s,"' will not be displayed..."

    def draw_text(self, gc, x, y, s, prop, angle, ismath=False):
        if self._last_clip is not None or self._last_clip_path is not None: self._reset_clip()
        t = time.time()
        #print "Draw", s, "at x:" ,x, "y:" , y, "angle", angle
        if ismath:
            self._draw_mathtext(gc, x, y, s, prop, angle)
            return
        angle = math.radians(angle)
        width, height, descent = self.get_text_width_height_descent(s, prop, ismath)
        x -= math.sin(angle) * descent
        y -= math.cos(angle) * descent
        ctx = self.ctx
        if angle != 0:
            ctx.save()
            ctx.translate(x, y)
            ctx.rotate(-angle)
            ctx.translate(-x, -y)
        #print "Font property: ", prop
        font_size = self.points_to_pixels(prop.get_size_in_points())
        font_str = '%s %s %.3gpx %s, %s' % (prop.get_style(), prop.get_weight(), font_size, prop.get_name(), prop.get_family()[0])
        ctx.font = font_str
        # Set the text color, draw the text and reset the color to black afterwards
        ctx.fillStyle = mpl_to_css_color(gc.get_rgb(), gc.get_alpha())
        ctx.fillText(unicode(s), x, y)
        ctx.fillStyle = '#000000'
        if angle != 0:
            ctx.restore()
        self._text_time = time.time() - t

    def _draw_mathtext(self, gc, x, y, s, prop, angle):
        """Draw math text using matplotlib.mathtext."""
        # Render math string as an image at the configured DPI, and get the image dimensions and baseline depth
        rgba, descent = self.mathtext_parser.to_rgba(s, color=gc.get_rgb(), dpi=self.dpi, fontsize=prop.get_size_in_points())
        height, width, tmp = rgba.shape
        angle = math.radians(angle)
        # Shift x, y (top left corner) to the nearest CSS pixel edge, to prevent resampling and consequent image blurring
        x = math.floor(x + 0.5)
        y = math.floor(y + 1.5)
        ctx = self.ctx
        if angle != 0:
            ctx.save()
            ctx.translate(x, y)
            ctx.rotate(-angle)
            ctx.translate(-x, -y)
        # Insert math text image into stream, and adjust x, y reference point to be at top left of image
        self._slipstream_png(x, y - height, rgba.tostring(), width, height)
        if angle != 0:
            ctx.restore()

    def flipy(self):
        return True

    def get_canvas_width_height(self):
        return self.width, self.height

    def get_text_width_height_descent(self, s, prop, ismath):
        if ismath:
            image, d = self.mathtext_parser.parse(s, self.dpi, prop)
            w, h = image.get_width(), image.get_height()
        else:
            font = self._get_font(prop)
            font.set_text(s, 0.0, flags=LOAD_NO_HINTING)
            w, h = font.get_width_height()
            w /= 64.0  # convert from subpixels
            h /= 64.0
            d = font.get_descent() / 64.0
        #print "String '%s' has dimensions w=%g h=%g d=%g" % (s, w, h, d)
        return w, h, d

    def new_gc(self):
        return GraphicsContextH5Canvas()

    def points_to_pixels(self, points):
        # The standard desktop-publishing (Postscript) point is 1/72 of an inch
        return points/72.0 * self.dpi
