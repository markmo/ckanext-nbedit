ckan.module('nbedit-stop-server', function ($) {
  return {
    initialize: function () {
      console.log('initializing module nbedit-stop-server');
      // console.log(this.options);
      this.isServerRunning = true;

      // if server is running
      if (!$('#nbeditor').length) {
        this.isServerRunning = false;
        // disable the 'Stop Server' button
        $('#stop-server-btn').attr('disabled', true);
      }
      this.el.on('click', $.proxy(this._onClick, this));
    },

    _onClick: function (ev) {
      // console.log('isServerRunning:', this.isServerRunning);
      if (!this.isServerRunning) {
        ev.preventDefault();
        return false;
      }
      $(this.el)
        .find('.text').text('Stopping...').end()
        .find('.fa-stop-circle').hide().end()
        .toggleClass('active');
    }
  };
});