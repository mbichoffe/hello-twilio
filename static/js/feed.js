$(document).ready(function($){
  // Enable pusher logging - don't include this in production
  Pusher.logToConsole = true;

  var pusher = new Pusher('00127d7d175b18006f04', {
    cluster: 'us2',
    forceTLS: true
  });
  var channel = pusher.subscribe('my-channel');
  channel.bind('check-in-event', function(data) {
    $('.feed').append('<h2>' + data.name + ' checked in!</h1>');
    $('#feed-bg').css('background-image', 'url("https://media.giphy.com/media/120ErahsQyf1q8/source.gif")');
  });

  $.get( "/v1/get-attendees", function(res) {
    console.log(res);
  });
});
