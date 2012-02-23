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

import numpy as np


class H5Frame(object):
    def __init__(self, frame_number=0, context_name='c'):
        self._frame_number = frame_number
         # the frame number in the current animated sequence
        self._context_name = context_name
         # the name of the context to use for drawing
        self._content = ""
         # a full frame of script ready for rendering
        self._extra = ""
        self._header = "frame_body_%s();" % self._context_name
        self._custom_header = False

    def _convert_obj(self, obj):
        return (isinstance(obj, unicode) and repr(obj.replace("'","`"))[1:] or (isinstance(obj, float) and '%.2f' % obj or repr(obj)))

    def __getattr__(self, method_name):
         # when frame is called in .<method_name>(<argument>) context
        def h5_method(*args):
            self._content += '%s.%s(%s);\n' % (self._context_name, method_name, ','.join([self._convert_obj(obj) for obj in args]))
        return h5_method

    def __setattr__(self, prop, value):
         # when frame properties are assigned to .<prop> = <value>
        if prop.startswith('_'):
            self.__dict__[prop] = value
            return
        self._content += '%s.%s=%s;\n' % (self._context_name, prop, self._convert_obj(value))

    def moveTo(self, x, y):
        self._content += '%s.%s(%.2f,%.2f);\n' % (self._context_name, "moveTo", x, y)

    def lineTo(self, x, y):
        self._content += '%s.%s(%.2f,%.2f);\n' % (self._context_name, "lineTo", x, y)
        #self._content = self._content + self._context_name + ".lineTo(" + str(x) + "," + str(y) + ");\n"
         # options for speed...

    def dashedLine(self, x1, y1, x2, y2, dashes):
        """Draw dashed line from (x1, y1) to (x2, y2), given dashes structure, and return new dash offset."""
        length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if length <= 0.0:
            return dashes[0]
        dash_length = np.sum(dashes[1])
        # Wrap offset to fall in interval [-dash_length..0], and do one dash period extra to ensure dashed line has no gaps
        offset, num_periods = -(dashes[0] % dash_length), int(length // dash_length) + 2
        unit_x, unit_y = (x2 - x1) / length, (y2 - y1) / length
        # The rest of the function can be implemented in Javascript instead, to compress the string being sent across the network
        self.moveTo(x1, y1)
        for n in xrange(num_periods):
            for m, dash_step in enumerate(dashes[1]):
                # Clip start of dash segment if it straddles (x1, y1)
                if offset < 0.0 and (offset + dash_step) > 0.0:
                    dash_step += offset
                    offset = 0.0
                # Clip end of dash segment if it straddles (x2, y2)
                if offset < length and (offset + dash_step) > length:
                    dash_step = length - offset
                # Advance to end of current dash segment
                offset += dash_step
                if offset >= 0.0 and offset <= length:
                    # Alternately draw dash and move to start of next dash
                    if m % 2 == 0:
                        self.lineTo(x1 + unit_x * offset, y1 + unit_y * offset)
                    else:
                        self.moveTo(x1 + unit_x * offset, y1 + unit_y * offset)
        return dashes[0] + (length % dash_length)

    def beginPath(self):
        self._content += '%s.%s();\n' % (self._context_name, "beginPath")

    def stroke(self):
        self._content += '%s.%s();\n' % (self._context_name, "stroke")

    def closePath(self):
        self._content += '%s.%s();\n' % (self._context_name, "closePath")

    def add_header(self, s, start=False):
        if not self._custom_header:
            self._custom_header = True
            self._header = ""
        if start: self._header = "%s\n" % s + self._header
        else: self._header += "%s\n" % s

    def write_extra(self, s):
        self._extra += '%s\n' % s

    def write(self, s):
        self._content += '%s\n' % s

    def get_frame(self):
        return "function frame_body_%s() { %s }\n" % (self._context_name, self._content)

    def get_frame_extra(self):
        return "function frame_body_%s() { %s\n%s }\n" % (self._context_name, self._extra, self._content)

    def get_header(self):
        return "function frame_header() { %s }\n" % self._header
        #return self._header

    def get_extra(self):
        return self._extra
