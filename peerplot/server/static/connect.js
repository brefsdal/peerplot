(function() {
    ConnectionManager = {
        socket: null,
        init: function (options) {
            this.options = $.extend({
                host: "peerplot.dce.harvard.edu",
                port: 80,
                session: "brian"
            }, options);
            var addr = 'ws://' + 
                this.options.host + ':' +
                this.options.port + '/manager/' +
                this.options.session;
            if (this.socket) {
                this.socket.close();
            }
            //this.socket = ("WebSocket" in window) ? new WebSocket(addr) : 
            //    new MozWebSocket(addr);
            if ("WebSocket" in window) {
                this.socket = new WebSocket(addr);
            } else {
                this.socket = new MozWebSocket(addr);
            }
            this.setupSocket();
        },
        setupSocket: function () {
            var self = this;
            var socket = this.socket;
            socket.onopen = function(e) {
                NameDialog.init({socket: socket});
            }
            socket.onmessage = function(e) {
                var params = {};
                var clients = [], admin = false, enabled = false;

                if (e.data) {
                    params = JSON.parse(e.data);

                    if (params !== null) {
                        clients = params.clients || [];
                        admin = params.admin || false;
                        enabled = params.enabled || false;
                    }

                    if (enabled) {
                        $('<div id="admin"></div>').appendTo("#plot_canvas");
                    }

                    params = { clients: clients, admin: admin };
                    if (params.admin) {
                        $("#admin").remove();
                        self.updateAdmin(params);
                        ClientDialog.addAdminButtons();
                    } else {
                        $("#admin").remove();
                        self.updateClient(params);
                        ClientDialog.addClientButtons();
                    }
                }
            }
            socket.onclose = function(e) {}
            socket.onerror = function(e) {}
        },
        updateAdmin: function (params) {
            var clients = params.clients || [];
            var list = "<select id='admin'>";
            for (var ii = 0; ii < clients.length; ii++) {
                var name = clients[ii].name;
                var disabled = (clients[ii].admin !== undefined) ? "disabled='True'" : "";
                // FIXME: make this a unique client key                
                list += "<option value='" + ii + "' " + disabled + ">" +
                    name + "</option>"; 
            }
            list += "</select>";
            $("#clientlist").html(list);
        },
        updateClient: function (params) {
            var clients = params.clients || [];
            var list = "<ul>";
            for (var ii = 0; ii < clients.length; ii++) {
                var name = clients[ii].name;
                var admin = (clients[ii].admin !== undefined) ? " (admin)" : "";
                list += "<li>"+clients[ii].name + admin + "</li>";
            }
            list += "</ul>";
            $("#clientlist").html(list);
        }
    };
})(jQuery);
