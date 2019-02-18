import os
from dotenv import load_dotenv, find_dotenv
from flask import Flask, request, redirect, url_for, render_template, jsonify
from http import HTTPStatus
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client
import requests
from requests import Request, Session
import phonenumbers
from flask_moment import Moment
from datetime import datetime
import pusher

app = Flask(__name__)
moment = Moment(app)

load_dotenv(find_dotenv())

#ENVIRONMENT VARIABLES
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID_P')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN_P')
TWILIO_SHORT_CODE = os.getenv('TWILIO_SHORT_CODE')
TWILIO_MESSAGING_SERVICE_SID = os.getenv('TWILIO_MESSAGING_SERVICE_SID')

SPLASHTHAT_CLIENT_SECRET = os.getenv('SPLASHTHAT_CLIENT_SECRET')
SPLASHTHAT_CLIENT_ID = os.getenv('SPLASHTHAT_CLIENT_ID')

NUMBERS = [os.getenv("TWILIO_NUMBERS")]



CLIENT = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
PASSWORD = os.getenv('PASSWORD')
PUSHER_ID = os.getenv('PUSHER_ID')
PUSHER_KEY = os.getenv('PUSHER_KEY')
PUSHER_SECRET = os.getenv('PUSHER_SECRET')

pusher_client = pusher.Pusher(
  app_id='638813',
  key='00127d7d175b18006f04',
  secret='b158e3dca09275556237',
  cluster='us2',
  ssl=True
)

EVENT_ID = '3277689'
EVENT_URL = "https://twilioafterhourslatinx.splashthat.com"
API_URL = "https://prod-api.splashthat.com"

ALL_GUEST_DICT = {}
GUESTS_WITHOUT_NUMBERS = {}

class Guest:
    def __init__(self, guest_dict, phone):
        self.id = str(guest_dict["id"])
        self.first_name = guest_dict["contact"]["first_name"]
        self.last_name = guest_dict["contact"]["last_name"]
        self.phone = phone

@app.route("/")
def home():
    token = get_access_token()
    # Get event data
    event_info_response = get_event_information(token, EVENT_ID)

    if event_info_response:
        title = event_info_response['title']
        description = event_info_response['meta_calendar_description']
        print(event_info_response['title'])
        start_time = datetime.strptime(event_info_response['start_time'], '%Y-%m-%dT%H:%M:%S')
        end_time = datetime.strptime(event_info_response['end_time'], '%Y-%m-%dT%H:%M:%S')


    return render_template('index.html',
        event_title=title,
        description=description,
        start_time= start_time,
        end_time= end_time)

@app.route("/feed")
def feed():
    return render_template('feed.html')

#let's not send initial messages and reminders for now
# @app.route("/v1/send-initial-message", methods=["POST"])
# def send_initial_message():
#     for guest in ALL_GUEST_DICT.values():
#         message = CLIENT.messages.create(
#             to=guest.phone,
#             from_=TWILIO_SHORT_CODE,
#             body="Hello! Thank you for RSVPing to the Tweek Science Fair. When you arrive at the event, check in by replying 'HERE' to this message. Come by the Hello Tweek booth to receive a small prize for your participation!")
#
#     return("Hello World")

# @app.route("/v1/send-reminder", methods=["POST"])
# def send_reminder():
#     failed = 0
#     for guest in ALL_GUEST_DICT.values():
#         try:
#             message = send_message(guest.phone, "Reminder! Tweek Science Fair is happening today at 2PM. Text from this number to check in.")
#         except TwilioRestException as e:
#             print(e)
#             failed +=1
#             continue
#     return jsonify({"message": "Reminder sent to guests with " + str(failed) + " failures"}), HTTPStatus.OK

@app.route("/v1/get-attendees", methods=["GET"])
def get_attendees():
    token = get_access_token()
    response = get_guests_list(token, EVENT_ID)
    # TODO: We know it is not necessary to pass env variable, but we will re-engineer this in the future
    try:
        response["guests"]
    except KeyError:
        return jsonify({"message": "Could not retrieve data"}), HTTPStatus.BAD_REQUEST

    total_guest_counter = 0
    error_counter = 0

    for guest in response["guests"]:
        if guest["contact"]["first_name"]:
            total_guest_counter += 1
        if guest["contact"]["phone"]:
                try:
                    phone_obj = phonenumbers.parse(guest["contact"]["phone"], "US")
                except phonenumbers.phonenumberutil.NumberParseException:
                    print("Guest {} {} entered {} which is not a phone number - but stored anyway".format(guest["contact"]["first_name"], guest["contact"]["last_name"], guest["contact"]["phone"]))
                    GUESTS_WITHOUT_NUMBERS[guest["contact"]["first_name"] + " " + guest["contact"]["last_name"]] = Guest(guest, None)
                    error_counter += 1
                    continue

                if phonenumbers.is_possible_number(phone_obj) and phonenumbers.is_valid_number(phone_obj):
                    phone = phonenumbers.format_number(phone_obj, phonenumbers.PhoneNumberFormat.E164)
                    print(phone)
                    ALL_GUEST_DICT[phone] = Guest(guest, phone)
                else:
                    GUESTS_WITHOUT_NUMBERS[guest["contact"]["first_name"] + " " + guest["contact"]["last_name"]] = Guest(guest, None)
                    print("Guest {} {} entered {} which is not a valid or possible phone number - but stored anyway.".format(guest["contact"]["first_name"], guest["contact"]["last_name"], guest["contact"]["phone"]))
                    error_counter += 1
                    continue
        else:
            found_phone_number = False
            for item in guest["answers"]:
                try:
                   phone_obj = phonenumbers.parse(item["answer"], "US")
                except phonenumbers.phonenumberutil.NumberParseException:
                    continue

                if phonenumbers.is_possible_number(phone_obj) and phonenumbers.is_valid_number(phone_obj):
                    phone = phonenumbers.format_number(phone_obj, phonenumbers.PhoneNumberFormat.E164)
                    ALL_GUEST_DICT[phone] = Guest(guest, phone)
                    print("Valid phone number {}, storing guest {}", phone, ALL_GUEST_DICT[phone])
                    found_phone_number = True

            if found_phone_number == False:
                possible_name = [guest["contact"]["first_name"], guest["contact"]["last_name"]]
                full_name = ' '.join(filter(None, possible_name))
                GUESTS_WITHOUT_NUMBERS[full_name] = Guest(guest, None)
                print("Couldn't find guest's {} {} phone on splashthat object - but stored anyway".format(guest["contact"]["first_name"], guest["contact"]["last_name"]))
                error_counter += 1

    print("Number of guests in dict is {}, with {} total guests ({} stored with no phone numbers)".format(len(ALL_GUEST_DICT), total_guest_counter, error_counter))

    return jsonify({"message": "All attendees gotten."}), HTTPStatus.OK


@app.route("/sms", methods=["POST"])
def incoming_message():

    phone_number = request.values.get('From', None)
    body = request.values.get('Body', None)
    # if the guest did not put their phone number in splashthat, they can enter their name in the body of the text

    resp = requests.post(url_for('check_in_guest', _external=True), json={"phone_number": phone_number, "body": body})
    # print(resp)
    return resp.content, resp.status_code

@app.route("/v1/checkin", methods=["POST"])
def check_in_guest():

    token = get_access_token()
    phone_number = request.get_json()['phone_number']
    body = request.get_json()['body']

    guest = fetch_registered_guest(phone_number, body)
    if guest:
        is_checked_in = splashthat_check_in(guest, token)
        if is_checked_in:
             # Call url that sends guest success message with guest.phone as param
            resp = send_message(guest.phone, "You are now checked in. Please enjoy the event!")

            if resp.status in ["queued", "accepted", "sending", "sent"]:
                 return jsonify({"message": "{} checked in".format(phone_number)}), HTTPStatus.OK
            else:
                 # TODO: This cannot be tested at this time. Needs status callbacks for proper testing

                 msg = "Guest {} {} was checked in successfully but we couldn't send confirmation SMS".format(
                     guest.first_name, guest.last_name)
                 print(msg)
                 return jsonify({"message": msg}), HTTPStatus.BAD_REQUEST
        else:
            send_message(guest.phone, "We could not check you in at this time. Please look for a Twilio volunteer "
                                      "for assistance. ")
            print("Failed to check in phone number {}".format(guest.phone))
            return jsonify({"message": "Failed to check in"}), HTTPStatus.INTERNAL_SERVER_ERROR

    else:
        resp = send_message(phone_number, "We could not find you in our guest list. "
                               "Please look for a Twilio volunteer for assistance.")
        if resp.status in ["queued", "accepted", "sending", "sent"]:
            msg = "Phone number {} not found in guest list".format(phone_number)
            print(msg)
            return jsonify({"message": msg}), HTTPStatus.OK
        else:
             # Guest is NOT checked in and failed to receive message
             # TODO: Will the initial status back from Twilio ever not be queued? NO
             # Would need status callbacks to properly verify that a message has not been delivered
             msg = "Phone number {} not found in guest list and we could not send confirmation SMS".format(
                 phone_number)
             print(msg)
             return jsonify({"message": msg}), HTTPStatus.BAD_REQUEST


def fetch_registered_guest(phone_number: str, message_body: str):
    """
    Rummages in ALL_GUESTS_DICT and GUESTS_WITHOUT_NUMBERS and confirms that this guest is registered
    :param phone_number, message_body
    :returns a guest object if guest is registered, None if guest is not registered
    """
    guest = ALL_GUEST_DICT.get(phone_number, None)

    if not guest:
        guest = GUESTS_WITHOUT_NUMBERS.get(message_body, None)
        if guest:
            # if the message body matches a key in GUESTS_WITHOUT_NUMBERS, add this phone number into their object
            guest.phone = phone_number
            GUESTS_WITHOUT_NUMBERS[message_body] = guest
            return guest

    return guest


def splashthat_check_in(guest: object, access_token: str) -> bool:
    """
    Calls SplashThat API to check in a guest
    If successful, returns success message -- otherwise it returns an error message
    :param: guest_id
    :return: True if request succeeds, False otherwise
    """

    headers = {'Authorization': 'Bearer ' + access_token}

    response = requests.put(API_URL +
                             "/groupcontact/" +
                             guest.id +
                             "/checkin",
                             headers=headers
                             )
    if response.ok:
        pusher_client.trigger('my-channel', 'check-in-event', { "name": guest.first_name + ' ' + guest.last_name})
        return True

    elif response.status_code == 409:
        print("user {} {} is already checked in.".format(guest.first_name, guest.last_name))
        return True

    else:
        print(response.status_code)
        print(response)
        print("error checking in {} {}".format(guest.first_name, guest.last_name))
        return False

def get_event_information(access_token:str, event_id:str):
    """
    :param access_token: string
    :param event_id: string
    :return: giant json
    """

    headers = {'Authorization': 'Bearer ' + access_token}

    response = requests.get(API_URL +
                            "/events/" +
                            event_id +
                            "/settings",
                            headers=headers)
    json = response.json()
    # If the response was successful and returned JSON has the value True
    # for the 'created' key
    if response.ok:
        return json["data"]
    else:
        return json["error_description"]

def get_guests_list(access_token:str, event_id:str):
    """
    :param token: string
    :param event_id: string
    :return: giant json
    """

    headers = {'Authorization': 'Bearer ' + access_token}

    response = requests.get(API_URL +
                            "/events/" +
                            event_id +
                            "/guestlist?limit=1000",
                            headers=headers)
    json = response.json()
    # If the response was successful and returned JSON then this has the value True
    # for the 'created' key
    if response.ok:
        return json["data"]
    else:
        return json["error_description"]

def get_access_token():
    """Use access code to request user's access token"""

    response = requests.get("https://api.splashthat.com/oauth/v2/token?client_id="+
                            SPLASHTHAT_CLIENT_ID+
                            "&client_secret="+
                            SPLASHTHAT_CLIENT_SECRET+
                            "&grant_type=password&scope=user&username="+
                            EMAIL_ADDRESS+
                            "&password="+
                            PASSWORD)

    json = response.json()

    if response.ok:
        access_token = json['access_token']
    # If there was an error, use None as the access token and
    # flash a message
    else:
        access_token = None
        print(f'OAuth failed: {json["error_description"]}')

    return access_token

def send_message(number:str, body:str=None)-> "twilio.rest.api.v2010.account.message.MessageInstance":
    message = CLIENT.messages.create(
        to=number,
        from_=TWILIO_MESSAGING_SERVICE_SID,
        body=body)
    return message

if __name__ == "__main__":
    app.run(debug=True)