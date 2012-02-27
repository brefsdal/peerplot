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
import webbrowser
import time
import datetime
import thread
import traceback
import cStringIO

import numpy as np
import cProfile as profile
from matplotlib._pylab_helpers import Gcf
from matplotlib.backend_bases import FigureCanvasBase, FigureManagerBase
from matplotlib.figure import Figure
from matplotlib.transforms import Affine2D

from peerplot.h5frame import H5Frame
from peerplot.rendererh5canvas import RendererH5Canvas

from peerplot import websocket

_test = False
_quiet = True
_metrics = False

figure_number = 0

HOST = 'peerplot.dce.harvard.edu'
PORT = '80'
SESSION_ID = ''

__all__ = ('FigureManagerH5Canvas', 'FigureManager', 'FigureCanvasH5Canvas',
           'draw_if_interactive', 'show', 'new_figure_manager')


def norm_angle(a):
    """Return angle between -180 and +180"""
    a = (a + 360) % 360
    if a > 180:
        a = a - 360
    return a


class FigureManagerH5Canvas(FigureManagerBase):
    """
    Wrap everything up into a window for the pylab interface

    For non interactive backends, the base class does all the work
    """
    def __init__(self, canvas, num):
        self.canvas = canvas
        FigureManagerBase.__init__(self, canvas, num)
        #print "Called init on figure manager",canvas,num

    def destroy(self, *args):
        self.canvas._stop_client()
        if not _quiet:
            print "Destroy called on figure manager",args

    def show(self):
        if not _quiet:
            print "Show called for figure manager"

########################################################################
#
# Now just provide the standard names that backend.__init__ is expecting
#
########################################################################

FigureManager = FigureManagerH5Canvas

class FigureCanvasH5Canvas(FigureCanvasBase):
    """
    The canvas the figure renders into.  Calls the draw and print fig
    methods, creates the renderers, etc...

    Public attribute

      figure - A Figure instance

    Note GUI templates will want to connect events for button presses,
    mouse movements and key presses to functions that call the base
    class methods button_press_event, button_release_event,
    motion_notify_event, key_press_event, and key_release_event.  See,
    eg backend_gtk.py, backend_wx.py and backend_tkagg.py
    """

    _server=None
    _thread=None

    def __init__(self, figure):
        FigureCanvasBase.__init__(self, figure)
        #print "Init of Canvas called....",figure
        self.frame_count = 0
        global figure_number
        self.figure_number = figure_number
        figure_number += 1
        self._clients = set()
        self._frame = None
        self._header = ""
        self._home_x = {}
        self._home_y = {}
        self._zoomed = False
        self._first_frame = True
        self._width, self._height = self.get_width_height()
        self.flip = Affine2D().scale(1, -1).translate(0, self._height)

        # Start WebSocket server
        try:
            self._server = websocket.WebSocketApp('ws://' + HOST + ':' + PORT + '/client/' + SESSION_ID,
                                                  on_open=self.web_socket_open,
                                                  on_message=self.web_socket_message,
                                                  on_close=self.web_socket_close,
                                                  on_error=self.web_socket_close)
            self._thread = thread.start_new_thread(self._server.run_forever, ())
        except Exception, e:
            print "Failed to create websocket server. (%s)" % str(e)
            #sys.exit(1)
            raise e


    def register_client(self, request):
        self._clients.add(request)

    def parse_web_cmd(self, s):
        action = s[1:s.find(" ")]
        args = s[s.find("args='")+6:-2].split(",")
        method = getattr(self, "handle_%s" % action, False)
        if method:
            try:
                method(*args)
            except Exception, e:
                trace = cStringIO.StringIO()
                traceback.print_exc(limit=None, file=trace)
                value = trace.getvalue()
                trace.close()
                if not _quiet:
                    print value, str(e)

        else:
            if not _quiet:
                print "Cannot find request method handle_%s" % action

    def show_browser(self):
        self.draw()
        #webbrowser.open_new_tab(h5m.url + "/" + str(self.figure.number))

    def handle_hello(self, *args):
        # if we have a lurking frame, send it on
        if self._frame is not None:
            self.send_frame(self._header + self._frame_extra)

    def handle_click(self, x, y, button):
        self.button_release_event(float(x),float(y),int(button))
        self.button_press_event(float(x), float(y), int(button))
         # currently we do not distinguish between press and release on the javascript side. So call both :)

    def handle_resize(self, width, height):
        width_in = float(width) / self.figure.dpi
        height_in = float(height) / self.figure.dpi
        self.figure.set_size_inches(width_in, height_in)
        self.draw()
         # set the figure and force a redraw...

    def handle_close(self, *args):
        # FIXME: don't kill the client if users still exist?
        self.figure.close()
        self._stop_client()

    def handle_home(self, *args):
         # reset the plot to it's home coordinates
        for i in self._home_x.keys():
            axes = self.figure.axes[i]
            axes.set_xlim(self._home_x[i][0], self._home_x[i][1])
            axes.set_ylim(self._home_y[i][0], self._home_y[i][1])
            if hasattr(axes, 'view_init'):
                axes.view_init(axes.initial_elev, axes.initial_azim)

        self._zoomed = False
        self.draw()

    def handle_zoom(self, ax, x0, y0, x1, y1):
         # these coordinates should be the bottom left and top right of the zoom bounding box
         # in figure pixels..
        ax = int(ax)

        if not _quiet:
            print 'Axes #', ax

        if not self._zoomed:
            self._home_x[ax] = self.figure.axes[ax].get_xlim()
            self._home_y[ax] = self.figure.axes[ax].get_ylim()
        self._zoomed = True
        inverse = self.figure.axes[ax].transData.inverted()
        lastx, lasty = inverse.transform_point((float(x0), float(y0)))
        x, y = inverse.transform_point((float(x1), float(y1)))
        x0, y0, x1, y1 = self.figure.axes[ax].viewLim.frozen().extents

        Xmin,Xmax=self.figure.axes[ax].get_xlim()
        Ymin,Ymax=self.figure.axes[ax].get_ylim()
        twinx, twiny = False, False
         # need to figure out how to detect twin axis here TODO

        if twinx:
            x0, x1 = Xmin, Xmax
        else:
            if Xmin < Xmax:
                if x<lastx:  x0, x1 = x, lastx
                else: x0, x1 = lastx, x
                if x0 < Xmin: x0=Xmin
                if x1 > Xmax: x1=Xmax
            else:
                if x>lastx:  x0, x1 = x, lastx
                else: x0, x1 = lastx, x
                if x0 > Xmin: x0=Xmin
                if x1 < Xmax: x1=Xmax

        if twiny:
            y0, y1 = Ymin, Ymax
        else:
            if Ymin < Ymax:
                if y<lasty:  y0, y1 = y, lasty
                else: y0, y1 = lasty, y
                if y0 < Ymin: y0=Ymin
                if y1 > Ymax: y1=Ymax
            else:
                if y>lasty:  y0, y1 = y, lasty
                else: y0, y1 = lasty, y
                if y0 > Ymin: y0=Ymin
                if y1 < Ymax: y1=Ymax

        self.figure.axes[ax].set_xlim((x0, x1))
        self.figure.axes[ax].set_ylim((y0, y1))
        self.draw()


    def handle_rotate(self, ax, x0, y0, x1, y1):
        # Matplotlib rotation API

        add_azim = 1.
        if (float(x0) - float(x1)) < 0:
            add_azim = -1.

        add_elev = 1.
        if (float(y0) - float(y1)) < 0:
            add_elev = -1.

        ax = int(ax)
        inverse = self.figure.axes[ax].transData.inverted()
        lastx, lasty = inverse.transform_point((float(x0), float(y0)))
        x, y = inverse.transform_point((float(x1), float(y1)))
        x0, y0, x1, y1 = self.figure.axes[ax].viewLim.frozen().extents

        Xmin,Xmax=self.figure.axes[ax].get_xlim()
        Ymin,Ymax=self.figure.axes[ax].get_ylim()
        twinx, twiny = False, False
         # need to figure out how to detect twin axis here TODO

        if twinx:
            x0, x1 = Xmin, Xmax
        else:
            if Xmin < Xmax:
                if x<lastx:  x0, x1 = x, lastx
                else: x0, x1 = lastx, x
                if x0 < Xmin: x0=Xmin
                if x1 > Xmax: x1=Xmax
            else:
                if x>lastx:  x0, x1 = x, lastx
                else: x0, x1 = lastx, x
                if x0 > Xmin: x0=Xmin
                if x1 < Xmax: x1=Xmax

        if twiny:
            y0, y1 = Ymin, Ymax
        else:
            if Ymin < Ymax:
                if y<lasty:  y0, y1 = y, lasty
                else: y0, y1 = lasty, y
                if y0 < Ymin: y0=Ymin
                if y1 > Ymax: y1=Ymax
            else:
                if y>lasty:  y0, y1 = y, lasty
                else: y0, y1 = lasty, y
                if y0 > Ymin: y0=Ymin
                if y1 < Ymax: y1=Ymax

        sx = float(x0); sy = float(y0); x = float(x1); y = float(y1)
        dx, dy = x - sx, y - sy
        x0, x1 = self.figure.axes[ax].get_xlim()
        y0, y1 = self.figure.axes[ax].get_ylim()

        # Reduce granularity by a factor of 2
        w = (x1-x0)*2.
        h = (y1-y0)*2.

        self.figure.axes[ax].sx = x
        self.figure.axes[ax].sy = y

        elev = self.figure.axes[ax].elev
        azim = self.figure.axes[ax].azim

        if dx != 0 and dy != 0:
            #self.figure.axes[ax].elev = norm_angle(elev - (dy/h)*180.)
            #self.figure.axes[ax].azim = norm_angle(azim - (dx/w)*180.)

            elev = norm_angle(elev - (dy/h)*180.*add_elev)
            azim = norm_angle(azim - (dx/w)*180.*add_azim)

            self.figure.axes[ax].view_init(elev, azim)

        if not _quiet:
            print " Setting angles"
        self.figure.axes[ax].get_proj()
        self.draw()


    def unregister_client(self, request):
        self._clients.remove(request)

    def web_socket_message(self, client, message=None):
        self.register_client(client)
        if message is None:
            #print 'connection closed...'
            return
        self.parse_web_cmd(message)

    def web_socket_open(self, client):
        #print 'opening websocket ...'
        client.sock.settimeout(None)

    def web_socket_close(self, client):
        #print 'closing websocket ...'
        client.send("close")
        self.unregister_client(client)

    def web_socket_send_data(self, request, message):
        #filename = datetime.datetime.now().isoformat('_') + '_backend_send.log'
        #f = file(filename, 'w')
        #f.write(message+'\n')
        #f.close()
        request.send(message)

    def send_frame(self, frame):
        #print 'sending frame....'
        for r in self._clients:
            self.web_socket_send_data(r, frame)


    def _stop_client(self):
        if self._server.sock:
            self.close()

    def close(self):
        if not _quiet: print "Stopping canvas web server..."
        self._server.close()


    def draw(self, ctx_override='c', *args, **kwargs):
        """
        Draw the figure using the renderer
        """
        ts = time.time()
        width, height = self.get_width_height()
        ctx = H5Frame(context_name=ctx_override)
         # the context to write the js in...
        renderer = RendererH5Canvas(width, height, ctx, dpi=self.figure.dpi)
        ctx.write_extra("resize_canvas(id," + str(width) + "," + str(height) + ");")
        ctx.write_extra("native_w[id] = " + str(width) + ";")
        ctx.write_extra("native_h[id] = " + str(height) + ";")
        #ctx.write("// Drawing frame " + str(self.frame_count))
        #ctx.write(ctx_override + ".width = " + ctx_override + ".width;")
         # clear the canvas...
        t = time.time()
        self.figure.draw(renderer)
        if _metrics:
            print "Render took %s s" % (time.time() - t)
            print "Path time: %s, Text time: %s, Marker time: %s, Sub time: %s" % (renderer._path_time, renderer._text_time, renderer._marker_time, renderer._sub_time)
        self.frame_count+=1
        for i,ax in enumerate(self.figure.axes):
            corners = ax.bbox.corners()
            bb_str = ""
            for corner in corners: bb_str += str(corner[0]) + "," + str(corner[1]) + ","
            ctx.add_header("ax_bb[" + str(i) + "] = [" + bb_str[:-1] + "];")
        if renderer._image_count > 0:
            ctx.add_header("var im_left_to_load_%s = %i;" % (ctx._context_name, renderer._image_count), start=True)
        else:
            ctx.add_header("frame_body_%s();" % ctx._context_name)
             # if no image we can draw the frame body immediately..
        self._header = ctx.get_header()
        self._frame = ctx.get_frame()
        self._frame_extra = ctx.get_frame_extra()
        # additional script commands needed for handling functions other than drawing
        self._width, self._height = self.get_width_height()
        # redo my height and width...

        self.send_frame(self._header + self._frame_extra)
        #self.tell()
        # if we have a frame ready, send it on...
        if self._first_frame:
            #self.tell()
            self._first_frame = False
        if _metrics: print "Overall draw took %s s, with %i clipcount" % ((time.time() - ts), renderer._clip_count)


    def show(self):
        if not _quiet:
            print "Show called... Not implemented in this function..."

    # You should provide a print_xxx function for every file format
    # you can write.

    # If the file type is not in the base set of filetypes,
    # you should add it to the class-scope filetypes dictionary as follows:
    filetypes = {'js': 'HTML5 Canvas'}

    def print_js(self, filename, *args, **kwargs):
        #print "Print js called with args",args,"and **kwargs",kwargs
        width, height = self.get_width_height()
        writer = open(filename, 'w')

        ctx = H5Frame(context_name='c')
        renderer = RendererH5Canvas(width, height, ctx, dpi=self.figure.dpi)
        self.figure.draw(renderer)
        for i,ax in enumerate(self.figure.axes):
            corners = ax.bbox.corners()
            bb_str = ""
            for corner in corners: bb_str += str(corner[0]) + "," + str(corner[1]) + ","
            ctx.add_header("ax_bb[" + str(i) + "] = [" + bb_str[:-1] + "];")
        if renderer._image_count > 0:
            ctx.add_header("var im_left_to_load_%s = %i;" % (ctx._context_name, renderer._image_count), start=True)
        else:
            ctx.add_header("frame_body_%s();" % ctx._context_name)
             # if no image we can draw the frame body immediately..
        header = ctx.get_header()
        frame = ctx.get_frame()
        frame_extra = ctx.get_frame_extra()
        # additional script commands needed for handling functions other than drawing

        # redo my height and width...
        writer.write(header + frame_extra)
        writer.close()


    def get_default_filetype(self):
        return 'js'


########################################################################
#
# The following functions and classes are for pylab and implement
# window/figure managers, etc...
#
########################################################################

def draw_if_interactive():
    """
    For image backends - is not required
    For GUI backends - this should be overriden if drawing should be done in
    interactive python mode
    """
    #print "In interactive..."
    pass

def show(block=True, layout='', open_plot=True):
    """
    This show is typically called via pyplot.show.
    In general usage a script will have a sequence of figure creation followed by a pyplot.show which
    effectively blocks and leaves the figures open for the user.
    We suspect this blocking is because the mainloop thread of the GUI is not setDaemon and thus halts
    python termination.
    To simulate this we create a non daemon dummy thread and instruct the user to use Ctrl-C to finish...
    """
    Gcf.get_active().canvas.draw()
    # update the current figure
    # open the browser with the current active figure shown...

    # if not _test and open_plot:
    #     try:
    #         webbrowser.open_new_tab(h5m.url + "/" + str(layout))
    #     except:
    #         print "Failed to open figure page in your browser. Please browse to " + h5m.url + "/" + str(Gcf.get_active().canvas.figure.number)

    if block and not _test:
        print "Showing figures. Hit Ctrl-C to finish script and close figures..."
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            if not _quiet:
                print "Shutting down..."


def new_figure_manager(num, *args, **kwargs):
    """
    Create a new figure manager instance
    """
    # if a main-level app must be created, this is the usual place to
    # do it -- see backend_wx, backend_wxagg and backend_tkagg for
    # examples.  Not all GUIs require explicit instantiation of a
    # main-level app (egg backend_gtk, backend_gtkagg) for pylab
    FigureClass = kwargs.pop('FigureClass', Figure)
    thisFig = FigureClass(*args, **kwargs)
    canvas = FigureCanvasH5Canvas(thisFig)
    manager = FigureManagerH5Canvas(canvas, num)
    #print "New figure created..."
    thisFig.__dict__['show'] = canvas.draw
    thisFig.__dict__['close'] = canvas.close
    thisFig.__dict__['show_browser'] = canvas.show_browser
     # provide a show that is basically just a canvas refresh...
    return manager
