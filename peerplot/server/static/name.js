(function() {
    NameDialog = {
        init: function (options) {
            this.options = $.extend({
                socket: null
            }, options);
            this.name = $("#name");
            this.allFields = $([]).add(this.name);
            this.tips = $(".validateTips");
            $("#dialog:ui-dialog").dialog("destroy");
            this.setupDialog();
            this.addButtons();
            $("#name-dialog").dialog("open");
        },
        setupDialog: function () {
            $("#name-dialog").dialog({
                autoOpen: false,
                height: 300,
                width: 350,
                modal: true,
                close: function () {
                    NameDialog.allFields.val("").removeClass("ui-state-error");
                }
            });
        },
        addButtons: function () {
            var self = this;
            $("#name-dialog").dialog("option", "buttons", {
                "Join Session": function() {
                    if(self.checkIfValid() && self.options.socket !== null) {
                        var msg = '{ "name" : "' + self.name.val() + '"}'
                        self.options.socket.send(msg);
                        plt.plotInit();
                        $(this).dialog("close");
                    }
                },
                Cancel: function () {
                    if (self.options.socket) {
                        self.options.socket.close();
                    }
                    $(this).dialog("close");
                }
            });
        },
        updateTips: function (t) {
            var self = this;
            self.tips.text(t).addClass("ui-state-highlight");
            setTimeout(function() {
                self.tips.removeClass("ui-state-highlight", 1500);
            }, 500);
        },
        checkLength: function (o, n, min, max) {
            if (o.val().length > max || o.val().length < min) {
                o.addClass("ui-state-error");
                this.updateTips("Length of " + n + " must be between " +
                                min + " and " + max + ".");
                return false;
            } else {
                return true;
            }
        },
        checkRegexp: function (o, regexp, n) {
            if (!( regexp.test(o.val()))) {
                o.addClass("ui-state-error");
                this.updateTips(n);
                return false;
            } else {
                return true;
            }
        },
        checkIfValid: function() {
            var bValid = true;
            var errMsg = "Usernames must consist of a-z, 0-9, " +
                "underscores, and must begin with a letter.";
            this.allFields.removeClass("ui-state-error");
            bValid = bValid && this.checkLength(this.name, "username", 3, 16);
            bValid = bValid && this.checkRegexp(this.name,
                         /^[a-z]([0-9a-z_])+$/i, errMsg);
            return bValid;
        }
    };
    ClientDialog = {
        init: function (options) {
            this.options = $.extend({
                socket: null
            }, options);
            $("#dialog:ui-dialog").dialog("destroy");
            this.setupDialog();
            this.setupButtons();
        },
        setupDialog: function () {
            $("#clientlist").dialog({
                autoOpen: false,
                height: 300,
                width: 350,
                modal: false,
                close: function () {}
            });
        },
        setupButtons: function () {
            if ($("#admin")) {
                this.addAdminButtons();
            }
            else {
                this.addClientButtons();
            }
        },
        addAdminButtons: function () {
            var self = this;
            $("#clientlist").dialog("option", "buttons", {
                "Make Admin": function () {
                    if ($("#admin").val() !== undefined &&
                        self.options.socket !== null) {
                        var msg = '{ "admin" : "' + $("#admin").val() + '"}';
                        self.options.socket.send(msg);
                        $("#clientlist").html("");
                        $(this).dialog("close");
                    }
                },
                Close: function () {
                    $(this).dialog("close");
                }
            });
        },
        addClientButtons: function () {
            $("#clientlist").dialog("option", "buttons", {
                Close: function () {
                    $(this).dialog("close");
                }
            });
        }
    };
})(jQuery);
