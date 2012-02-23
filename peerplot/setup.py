#!/usr/bin/env python
"""
PeerPlot - matplotlib on the cloud

Copyright (c) 2012, Brian Refsdal (brian.refsdal@gmail.com)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""


from setuptools import setup

setup (
    name = "peerplot",
    version = "0.0.4",
    description = "PeerPlot: Collaborative Plotting on the Cloud",
    url = "http://peerplot.com",
    author = "Brian Refsdal",
    author_email = "brian.refsdal@gmail.com",
    license = "BSD",
    classifiers=["Environment :: Console",
                 "Intended Audience :: Developers",
                 "Intended Audience :: End Users/Desktop",
                 "License :: OSI Approved :: BSD License",
                 "Operating System :: OS Independent",
                 "Programming Language :: Python :: 2",
                 "Topic :: Software Development :: Libraries :: Python Modules",
                 ],
    packages = ['peerplot'],
    scripts = [],
    zip_safe = False,
    #    data_files=[
    #        ('examples', []),
    #
    #                ]
)
