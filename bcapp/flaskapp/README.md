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

## Web Front End

Please [see these docs](docs/users.md) for information on the web front end.

## Bypass Censorship API

The API has two functions: 

- Returns alternatives on request (can be public or authenticated)
- Takes domain and alternative reports (authenticated)

The API uses auth tokens just to protect from spurious/malicious requests and/or reporting. You'll likely want to do this to the database before you run the app:

`INSERT INTO auth_tokens (id, auth_token) VALUES ('1','some auth token here')`

Then you'll add that auth_token to the **Authorization** header in the request to the API.

### API requests for Alternatives

You can choose for this to be public or authenticated. In the auto.cfg file, under [SYSTEM] see api_requests. That value can be 'public' or 'auth'.

A request with the following format ([see this](json_request.json):

```
{
    "url":"testing.com"
}
```

The API will return this JSON:
```
{
"alternatives" : [
        {
            "proto": "https",
            "type": "proxy",
            "url": "dekksjabdkalsps.cloudfront.com"
        },
        {
                "proto": "tor",
                "type": "eotk",
                "url": "https://hsaduiabaweuhwiuegwqeiquwbe.onion"
        }
    ]
}
```
The URL to request alternatives to a current URL is http(s)://host/api/v2/alternatives

### API reporting

This is always authenticated. A request with [this format](json_report.json) will return this json:
```
{
    "report_result":"http status code"
}
```

The URL for reporting is: http(s)://host/api/v2/report. 


