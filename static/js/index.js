$(document).ready(function($){
    $("#getAttendees").on("click", function(e){
      e.preventDefault();
      $.get( "/v1/get-attendees", function(data) {
        $(".result").html(data.message);
      });
    });
});
