"""
Bypass Censorship API

Allows for testing and requests for BP mirrors from an API

"""
from flask import Flask
from ..mirror_tests import mirror_detail

app = Flask(__name__)

@app.route('/')
def help():
    """
    Return help info in JSON format
    """
    return {"help" : "is on the way"}

@app.route('/domain/<domain>')
def test_domain(domain):
    """
    Return domain test info
    """
    detail = mirror_detail(domain, False, True)
    return detail