(function($) {

    // canvas dimenions are determined by height and width of placeholder <div>
    function Plot(placeholder, options) {

        var canvas = null,  // the canvas for the plot itself
        overlay = null,     // canvas for interactive stuff on top of plot
        eventHolder = null, // jQuery object that events should be bound to
        ctx = null, octx = null,
        plotOffset = { left: 0, right: 0, top: 0, bottom: 0},
        canvasWidth = 0, canvasHeight = 0,
        plotWidth = 0, enabled = true, plotHeight = 0,
        host = "peerplot.dce.harvard.edu", port = 80, session = "brian",
        plotSocket = false, isPlotting = false,
        lastFrame = "var frame_header = false;",
        plot = this, cursor_info = 0;
        var plotCanvas = document.getElementById('plot_canvas');

        // limit and zoom divs
        var ldiv = [], startX = 0, startY = 0, stopX = 0, stopY = 0, zdraw = -1, ztop = 0;
        var move = -1, resize = -1, rStartX = 0, rStartY = 0, mStartX = 0, mStartY = 0;

        // Public function
        plot.plotInit = function () {

            if (!isPlotting) {

                var addr = 'ws://' + host + ':' + port + '/api/' + session;
                if ("WebSocket" in window) {
                    plotSocket = new WebSocket(addr);
                } else {
                    plotSocket = new MozWebSocket(addr);
                }

                document.getElementById('status').innerText = "Connecting to port " + port + "...";

                plotSocket.onopen = function(e) {
                    plotSocket.send("<hello args=''");
                }

                plotSocket.onmessage = function(e) {
                    document.getElementById('status').innerText = "Connected";
                    lastFrame = e.data;
                    drawFrame(ctx);
                }

                plotSocket.onclose = function(e) {
                    isPlotting = false;
                }

                isPlotting = true;
            }
        }

        // Init
        parseOptions(options);
        setupCanvases();
        resize_canvas(0, canvasWidth, canvasHeight);

        // Set up event callbacks
        $("#plotBody").mouseup(function (e) { outSize(); });

        $("#zoom_div").mousemove(function(event) { slideCanvas(event, this); });
        $("#zoom_div").mouseup(function(event) {

            if ( event.which == 1 ) {
                releaseCanvas(event, this);
            }

        });

        $("#hb").click(function(event) { goHome(); });
        $("#hb").bind("ondragstart", function(event) { return false; });

        $("#mb").click(function(event) { maximize(); });
        $("#mb").bind("ondragstart", function(event) { return false; });

        $("#sm").mousedown(function(event) { clickMove(event); });
        $("#cm").mousedown(function(event) { clickMove(event); });

        $("#cursor_info").click(function(event) { trackCursor(); });

        $("#cb").click(function(event) { closePlot(); });

        $("#rb").bind("ondragstart", function(event) { return false; });

        $("#rbb").mousedown(function(event) { clickSize(event); });

        $("#plotDiv").bind("ondragover", function(event) { onDragOver(event, this); });
        $("#plotDiv").bind("ondrop", function(event) { onDrop(event); });
        $("#plotDiv").mouseup(function(event) { releaseCanvas(event, this); });

        // Private Functions

        function parseOptions(options) {
            if( options.host !== undefined )
                host = options.host;
            if( options.host !== undefined )
                port = options.port;
            if( options.host !== undefined )
                session = options.session;
            if( options.width !== undefined )
                canvasWidth = options.width;
            if( options.height !== undefined )
                canvasHeight = options.height;
        }

        // This signature must be (id, width, height)!
        // Called by payload
        function resize_canvas(id, width, height) {
            canvasWidth = width;
            canvasHeight = height;
            resizeCanvas(canvas);
            resizeCanvas(overlay);
            placeholder.width(width);
            placeholder.height(height);
            document.getElementById("button_menu").style.width = width + "px";
        }

        function slideCanvas(e) {
            var pageX = getPageX(e);
            var pageY = getPageY(e);
            var xDelta = pageX - startX;
            var yDelta = pageY - startY;

            if (!e) { var e = window.event; }
            if (zdraw > -1)  {
                var zdiv = document.getElementById("zoom_div");
                var offsetTop = (plotCanvas.offsetTop + plotCanvas.offsetParent.offsetTop);
                var offsetLeft = (plotCanvas.offsetLeft + plotCanvas.offsetParent.offsetLeft);
                var startYTop = (startY - offsetTop) + "px";
                var startXLeft = (startX - offsetLeft) + "px";
                var pageYTop = (pageY - offsetTop) + "px";
                var pageXLeft = (pageX - offsetLeft) + "px";
                // IV quad
                if (xDelta > 0 && yDelta > 0) {
                    //zdiv.style.top = (startY - (plotCanvas.offsetTop + plotCanvas.offsetParent.offsetTop)) + "px";
                    //zdiv.style.left = (startX - (plotCanvas.offsetLeft + plotCanvas.offsetParent.offsetLeft)) + "px";
                    zdiv.style.top = startYTop;
                    zdiv.style.left = startXLeft;
                }
                // II quad
                if (xDelta < 0 && yDelta < 0) {
                    //zdiv.style.top = (pageY - (plotCanvas.offsetTop + plotCanvas.offsetParent.offsetTop)) + "px";
                    //zdiv.style.left = (pageX - (plotCanvas.offsetLeft + plotCanvas.offsetParent.offsetLeft)) + "px";
                    zdiv.style.top = pageYTop;
                    zdiv.style.left = pageXLeft;
                }
                // I quad
                if (xDelta > 0 && yDelta < 0) {
                    //zdiv.style.top = (pageY - (plotCanvas.offsetTop + plotCanvas.offsetParent.offsetTop)) + "px";
                    //zdiv.style.left = (startX - (plotCanvas.offsetLeft + plotCanvas.offsetParent.offsetLeft)) + "px";
                    zdiv.style.top = pageYTop;
                    zdiv.style.left = startXLeft;
                }
                // III quad
                if (xDelta < 0 && yDelta > 0) {
                    //zdiv.style.top = (startY - (plotCanvas.offsetTop + plotCanvas.offsetParent.offsetTop)) + "px";
                    //zdiv.style.left = (pageX - (plotCanvas.offsetLeft + plotCanvas.offsetParent.offsetLeft)) + "px";
                    zdiv.style.top = startYTop;
                    zdiv.style.left = pageXLeft;
                }
                zdiv.style.width = Math.abs(xDelta) + "px";
                zdiv.style.height = Math.abs(yDelta) + "px";
            }

            // If zooming
            if ($("#zoom").is(":checked")) {
                document.getElementById('cursor_info').innerText = "Cursor at: " + pageX + "," + pageY;
            }
            else {
                if (startX != 0 && startY != 0) {  
                    // Reduce granularity by a factor of 2.
                    var w = canvasWidth * 2.;
                    var h = canvasHeight * 2.;

                    var elev_delta = (yDelta/h)*180.;
                    var azim_delta = (xDelta/w)*180.;

                    document.getElementById('cursor_info').innerText = "Delta (deg): " +
                        azim_delta.toFixed(1) + ", " + elev_delta.toFixed(1);
                }
            }
            return false;
        }

        function releaseCanvas(e, zdiv) {
            var pageX = getPageX(e);
            var pageY = getPageY(e);

            if ($("#admin").length > 0) {
                stopX = pageX;
                stopY = pageY;
                var zdiv = document.getElementById("zoom_div");
 
                // Support rotation in NW, SW, and NE directions
                if (zdraw > -1 && (Math.abs(stopX-startX)>2) && (Math.abs(stopY-startY)>2)) {
                    zoom(zdiv, zdraw);
                }
                else {
                    // not in zdraw (or zoomed areas less than 5x5) so normal click
                    handleClick(e);
                    zdiv.style.display = "none";
                }
                startX  = stopX = startY = stopY = 0;
            }
            zdraw = -1;
            return false;
        }

        function zoom(zdiv, axes) {
            var zoom_coords = axes +
                "," +
                (startX - plotCanvas.offsetLeft) +
                "," +
                (canvasHeight - (stopY - plotCanvas.offsetTop)) +
                "," +
                (stopX - plotCanvas.offsetLeft) +
                "," +
                (canvasHeight - (startY - plotCanvas.offsetTop));

            var zoom_or_rotate = $("#zoom").is(":checked") ? "zoom" : "rotate";
            plotSocket.send("<" + zoom_or_rotate + " args='" + zoom_coords + "'>");
            zdiv.style.width = "0px";
            zdiv.style.height = "0px";
            zdiv.style.display = "none";
        }

        function clickCanvas(e, axes) {
            var pageX = getPageX(e);
            var pageY = getPageY(e);

            if (!e) { var e = window.event; }
            if ($("#admin").length > 0 && (e.button === 0) && (e.shiftKey === false)) {
                var zdiv = document.getElementById('zoom_div');
                zdraw = axes;
                zdiv.style.width = 0;
                zdiv.style.height = 0;
                zdiv.style.top = (pageY - (plotCanvas.offsetTop + plotCanvas.offsetParent.offsetTop)) + "px";
                zdiv.style.left = (pageX - (plotCanvas.offsetLeft + plotCanvas.offsetParent.offsetLeft)) + "px";
                zdiv.style.display = "inline";
                startX = pageX;
                startY = pageY;
            }
            return false;
        }

        function clickMove(e) {
            var pageX = getPageX(e);
            var pageY = getPageY(e);

            move = 0;
            mStartY = (pageY - plotCanvas.offsetTop);
            mStartX = (pageX - plotCanvas.offsetLeft);
            ztop += 1;
            plotCanvas.style.setProperty('z-index',ztop);
        }

        function trackCursor() {
            document.getElementById('cursor_info').innerText = "";
            cursor_info += 1;
            if (cursor_info > 1) {
                cursor_info = 0;
            }
        }

        function closePlot() {
            if ($("#admin").length > 0) {
                plotSocket.send("<close args=''>");
                stopPlotting();
            }
        }

        function stopPlotting() {

            plotSocket.onmessage = function(e) {};

            // reset the handler so that the buffer behind this socket does not polute new plots
            plotSocket.close();
            lastFrame = "var frame_header = false;";
            document.getElementById('status').innerText = "Disconnected";

            isPlotting = false;
        }

        function clickSize(e) {
            var pageX = getPageX(e);
            var pageY = getPageY(e);
            if ($("#admin").length > 0) {
                var cr = document.getElementById('resize_div');
                resize = 0;
                rStartX = pageX;
                rStartY = pageY;
                document.getElementById('status').innerText = "Click size at " + rStartX + "," + rStartY;
                cr.style.top = plotCanvas.style.top;
                cr.style.left = plotCanvas.style.left;
                cr.style.width = (plotCanvas.clientWidth  - 2) + "px";
                cr.style.height = (plotCanvas.clientHeight  - 4) + "px";
                cr.style.display = "inline";
            }
            return false;
        }

        function slideSize(e) {
            var pageX = getPageX(e);
            var pageY = getPageY(e);
            if ($("#admin").length > 0 && resize > -1) {
                var cr = document.getElementById('resize_div');
                cr.style.width = (pageX - cr.offsetLeft) + "px";
                cr.style.height = (pageY - cr.offsetTop) + "px";
                document.getElementById('status').innerText = "Slide size to " +
                    (pageX - rStartX) + "," + (pageY - rStartY);
            }
            else if (move > -1) {
                plotCanvas.style.top = (pageY - mStartY) + "px";
                plotCanvas.style.left = (pageX - mStartX) + "px";
            }
            return false;
        }

        function getPageX(e) {
            return (window.Event) ? e.pageX : e.clientX + (document.documentElement.scrollLeft ? document.documentElement.scrollLeft : document.body.scrollLeft);
        }

        function getPageY(e) {
            return (window.Event) ? e.pageY : e.clientY + (document.documentElement.scrollTop ? document.documentElement.scrollTop : document.body.scrollTop);
        }

        function getDocWidth() {
            return Math.max(
                $(document).width(),
                $(window).width(),
                document.documentElement.clientWidth
            );
        };

        function getDocHeight() {
            return Math.max(
                $(document).height(),
                $(window).height(),
                document.documentElement.clientHeight
            );
        };

        function maximize() {
            if ($("#admin").length > 0) {
                var w = getDocWidth() * 0.98 - plotCanvas.offsetLeft;
                var h = getDocHeight() * 0.98 - plotCanvas.offsetTop - 20;
                resize = 0;
                doResize(w, h);
                resize = -1;
            }
        }

        function outSize() {
            if ($("#admin").length > 0 && resize > -1) {
                var cr = document.getElementById('resize_div');
                doResize(cr.clientWidth, cr.clientHeight - 20);
                cr.style.display = "none";
            }
            resize = -1;
            move = -1;
            zdraw = -1;
            // make sure we kill everything on mouse up
        }

        function doResize(w, h) {
            if (resize > -1) {
                try {
                    plotSocket.send("<resize args='" + w + "," + h + "'>");
                } catch (err) {}
            }
            else {
                var xScale = w / native_w[0];
                var yScale = h / native_h[0];
                resize_canvas(0, w, h);
                // no figure active for this canvas so do a purely client side resize
                //allow_resize = false;
                //canvii[id].width = canvii[id].width;
                // clear the canvas and reset scale factor before client size redraw
                document.getElementById('status').innerText = "Client side resize mode";
                ctx.scale(xScale, yScale);
                // needs to be done after resize_canvas, but this loses canvii[id].width/height so extra vars needed
                drawFrame(ctx);
                // the frame we draw may contain resize commands. Ignore these in client only mode hence the bracketing allow_resize directives.
                //allow_resize = true;
            }
        }

        function goHome() {
            if($("#admin").length > 0) {
                plotSocket.send("<home args=''>");
            }
        }

        function handleClick(e) {
            var pageX = getPageX(e);
            var pageY = getPageY(e);

            if ($("#admin").length > 0) {
                plotSocket.send("<click args='" +
                                (pageX - plotCanvas.offsetLeft) + "," +
                                (canvasHeight - (pageY - plotCanvas.offsetTop)) + "," +
                                (e.button + 1) + "'>");
            }
        }

        function onDragOver(e, div) {
            if (e.preventDefault) { e.preventDefault(); }
            div.className = 'over';
            e.dataTransfer.dropEffect = 'copy';
            return false;
        }

        function onDrop(e) {
            if (e.preventDefault) { e.preventDefault(); }
            // stop Firefox triggering a page change event
            //top_e = e;
            var dt= e.dataTransfer;
            console.log(dt);
            //var el_id = e.dataTransfer.getData('Text');

            // FIXME: stop plotting when canvas is resized??
            //stopPlotting();
            return false;
        }

        function makeLimitDiv(nid, i) {
            var div = $('<div class="cursor"></div>');
            div.attr('id', nid);
            div.mousemove(function (e) {slideCanvas(e, this);});
            div.mousedown(function (e) {

                if ( e.which == 1 ) {
                    clickCanvas(e, i);
                }

            });
            div.mouseup(function (e) {releaseCanvas(e, this);});
            div.bind('ondragover', function (e) { onDragOver(e, this); });
            div.bind('ondrop', function (e) { onDrop(e); });
            return div;
        }

        function updateLimitDiv(ax_bb) {

            ldiv = [];
            for (var i=0; i < ax_bb.length; i++) {
                var nid = 'limit_div_' + i;
                for(var j=0; j < plotCanvas.childNodes.length; j++) {
                    var child = plotCanvas.childNodes[j];
                    if( child.id !== undefined && child.id == nid )
                        plotCanvas.removeChild(child);
                }

                var ndiv = makeLimitDiv(nid, i);
                ndiv.appendTo($("#plot_canvas"));
                ldiv[i] = document.getElementById(nid);
                ldiv[i].style.display = "inline";
                ldiv[i].style.left = ax_bb[i][0] + "px";
                ldiv[i].style.top = ax_bb[i][1] + "px";
                ldiv[i].style.width = ax_bb[i][4] - ax_bb[i][0] + "px";
                ldiv[i].style.height = ax_bb[i][3] - ax_bb[i][1] + "px";
            }

        }
        function drawFrame(c)   {
            var ax_bb = [], native_w = [], native_h = [], id = 0;

            eval(lastFrame);
            if(frame_header) {
                frame_header();
            }
            //document.getElementById("info").innerHTML = ax_bb.toString();

            updateLimitDiv(ax_bb);
      }

        function makeCanvas(skipPositioning, cls) {
            var c = document.createElement('canvas');
            c.className = cls;
            c.width = canvasWidth;
            c.height = canvasHeight;

            if (!skipPositioning)
                $(c).css({ position: 'absolute', left: 0, top: 0, border: '1px solid gray' });

            $(c).appendTo(placeholder);

            if (!c.getContext) // excanvas hack
                c = window.G_vmlCanvasManager.initElement(c);

            // used for resetting in case we get replotted
            c.getContext("2d").save();

            return c;
        }

        function resizeCanvas(c) {
            // resizing should reset the state (excanvas seems to be
            // buggy though)
            if (c.width != canvasWidth)
                c.width = canvasWidth;

            if (c.height != canvasHeight)
                c.height = canvasHeight;

            // so try to get back to the initial state (even if it's
            // gone now, this should be safe according to the spec)
            var cctx = c.getContext("2d");
            cctx.restore();

            // and save again
            cctx.save();
        }

        function getCanvasDimensions() {
            canvasWidth = placeholder.width();
            canvasHeight = placeholder.height();

            if (canvasWidth <= 0 || canvasHeight <= 0)
                throw "Invalid dimensions for plot, width = " + canvasWidth + ", height = " + canvasHeight;
        }

        function setupCanvases() {
            var reused,
                existingCanvas = placeholder.children("canvas.base"),
                existingOverlay = placeholder.children("canvas.overlay");

            if (existingCanvas.length == 0 || existingOverlay == 0) {
                // init everything

                placeholder.html(""); // make sure placeholder is clear

                placeholder.css({ padding: 0 }); // padding messes up the positioning

                if (placeholder.css("position") == 'static')
                    placeholder.css("position", "relative"); // for positioning labels and overlay

                getCanvasDimensions();

                canvas = makeCanvas(true, "base");
                overlay = makeCanvas(false, "overlay"); // overlay canvas for interactive features

                reused = false;
            }
            else {
                // reuse existing elements

                canvas = existingCanvas.get(0);
                overlay = existingOverlay.get(0);

                reused = true;
            }

            ctx = canvas.getContext("2d");
            octx = overlay.getContext("2d");

            // we include the canvas in the event holder too, because IE 7
            // sometimes has trouble with the stacking order
            eventHolder = $([overlay, canvas]);

            if (reused) {
                // run shutdown in the old plot object
                placeholder.data("plot").shutdown();

                // reset reused canvases
                plot.resize();

                // make sure overlay pixels are cleared (canvas is cleared when we redraw)
                octx.clearRect(0, 0, canvasWidth, canvasHeight);

                // then whack any remaining obvious garbage left
                eventHolder.unbind();
                placeholder.children().not([canvas, overlay]).remove();
            }

            // save in case we get replotted
            placeholder.data("plot", plot);
        }

        // Contributed by Charles Blackwell
        // http://stackoverflow.com/questions/8208043/display-google-map-on-hover-link-or-text
        if (window.Event) {
            document.captureEvents(Event.MOUSEMOVE);
        }
        document.onmousemove = slideSize;
        document.addEventListener("onmousemove", slideSize, true);
    }

    $.plot = function(placeholder, options) {
        var plot = new Plot($(placeholder), options);
        return plot;
    };

})(jQuery);
