ckan.module('nbedit-start-server', function ($) {
  return {
    initialize: function () {
      console.log('initializing module nbedit-start-server');
      // console.log(this.options);

      // if server is running
      if ($('#nbeditor').length) {
        this.isServerRunning = true;
        // disable the 'Start Server' button
        $('#start-server-btn').attr('disabled', true);
      }
      this.el.on('click', $.proxy(this._onClick, this));
    },

    _onClick: function (ev) {
      // console.log('isServerRunning:', this.isServerRunning);
      if (this.isServerRunning) {
        ev.preventDefault();
        return false;
      }
      $(this.el)
        .find('.text').text('Starting...').end()
        .find('.fa-server').hide().end()
        .toggleClass('active');
    }
  };
});