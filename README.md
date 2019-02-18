# Hello Twilio
## Tweek 8.5 Project

Python 3 Flask App

### Short description
Currently our checkin procedure for Twilio After Hours is not automated. This creates a checkin bottleneck that is detrimental to the experience of our event attendees. Using our Messaging software and the Splashthat API, we want to create an automated checkin system.

### Departments impacted
Engineering, recruiting, messaging, and marketing

### Team
- Elizabeth Acosta
- Marina Bichoffe
- Lyra Hall
- Kyle Woumn
- Lupita Davila
- Mel Chang

#### Set up your local environment variables

Go to your tweek-hello-twilio project folder. You will need a .env file, and the quickest way to do that is to use our .env.example file, which is part of the github repo, by copying it over:

```
cp .env_example .env
```

Add the values from your Twilio.com account to the file.

#### Setting up venv and running server:

 * Run `python -m venv venv` in your home directory (it might be python3 depending on what you've got locally)
 
 * A venv folder should appear in your directory. 

 * Run `source venv/bin/activate`

 * Run `pip install -r requirements.txt`

 * Run `python main.py` and go to localhost:5000

 * The project is run locally on ngrok. The command is `ngrok http -subdomain=lyra 5000`, which only works on Lyra's computer.

 * The above ngrok url is configured on the shortcode, with Marina's ngrok subdomain as a backup.
