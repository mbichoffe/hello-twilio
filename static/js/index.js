$(document).ready(function($){
    $("#getAttendees").on("click", function(e){
      e.preventDefault();
      $.get( "/v1/get-attendees", function(data) {
        $(".result").html(data.message);
      });
    });

    $("#sendReminder").on("click", function(e){
      e.preventDefault();
      $.post( "/v1/send-reminder", function(data) {
        console.log(data);
        console.log("In the post!");
        $(".result").html(data.message);
      }).fail(function(e){
        $(".result").html("Could not send reminders");
      });
    });
});
