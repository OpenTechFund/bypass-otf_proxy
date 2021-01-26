# Installation/setup

You'll need to set up a postgresql database, which the flask app has permission to access.

Use the .env_example to create an .env file. Python-dotenv is a module that will read the .env files automatically.

To start up the app, make sure you've started the virtual environment, then `cd bcapp\flaskapp`.

The first time you run the app, set up the database:

```
flask db init
flask db migrate
flask db upgrade
```

Then run the app:

`flask run`

(or `flask run &` if you want it to run in the background.)

It will be running on port 5000. This is for development purposes only.

## Bypass Censorship API

The API uses auth tokens just to protect from spurious/malicious reporting. You'll likely want to do this to the database before you run the app:

`INSERT INTO auth_tokens (id, auth_token) VALUES ('1','some auth token here')`

Then you'll add that auth_token to the Authorization header in the request to the API.

This api (bcapp/api) can take reports from the Bypass Censorship Browser extension (and eventually interface with proxies and mirrors.) This is currently a work in progress.

The URL to request alternatives to a current URL is http(s)://host/api/v2/alternatives

The file bcapp/flaskapp/json_request.json is the format for the json request to the API for information about alternatives to the domain

The URL for reporting is: http(s)://host/api/v2/report (development purposes). The file bcapp/flaskapp/json_report.json is the format for reporting to the API about domain/url status.

## Reports available

### Query for alternatives

On the home page is a menu which allows you to display links to the alternatives for a domain in that menu list, as well as tests on the fly whether or not the domain and alternatives are live.

### Administrative Reports

The Flask application at http://host:5000/ presents a screen with a login menu item. If you haven't set up a user yet, you can go access this url: http://host:5000/signup, and add a user. Go into the database, and set 'active' and 'admin' for that user you just created to 'True' (they are boolean fields.) When you log in, and you choose 'Admin' from the upper right menu, you'll see these reports:

- Recent Domain Reports - list of the last several reports on domains from the API and command-line reporting tool - choose a domain you want to report on
- Last Week's Bad Domains - list of the bad domains from the API and command-line reporting tool
- Last Week's Bad Mirrors - list of the bad mirrors from the API and command-line reporting tool
- Monthly aggregate report - aggregates the number of reports per domain/mirror for the month




