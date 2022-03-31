from datetime import datetime

import boto3 as boto3
from flask import Flask, jsonify, render_template, Response, redirect, url_for
import yaml

from app.extensions import db
from app.extensions import migrate
from app.extensions import bootstrap
from app.mirror_sites import mirror_sites
from app.models import Group, Origin, Proxy, Mirror
from app.portal import portal

app = Flask(__name__)
app.config.from_file("../config.yaml", load=yaml.safe_load)
db.init_app(app)
migrate.init_app(app, db, render_as_batch=True)
bootstrap.init_app(app)

app.register_blueprint(portal, url_prefix="/portal")


@app.route('/')
def index():
    return redirect(url_for("portal.portal_home"))


@app.route('/mirrors')
def list_mirrors():
    res = Mirror.query.all()
    return render_template("mirrors.html", mirrors=res)


@app.route('/import/cloudfront')
def import_cloudfront():
    a = ""
    not_found = []
    cloudfront = boto3.client('cloudfront',
                              aws_access_key_id=app.config['AWS_ACCESS_KEY'],
                              aws_secret_access_key=app.config['AWS_SECRET_KEY'])
    dist_paginator = cloudfront.get_paginator('list_distributions')
    page_iterator = dist_paginator.paginate()
    for page in page_iterator:
        for dist in page['DistributionList']['Items']:
            res = Proxy.query.all()
            matches = [r for r in res if r.origin.domain_name == dist['Comment'][8:]]
            if not matches:
                not_found.append(dist['Comment'][8:])
                continue
            a += f"# {dist['Comment'][8:]}\n"
            a += f"terraform import module.cloudfront_{matches[0].id}.aws_cloudfront_distribution.this {dist['Id']}\n"
    for n in not_found:
        a += f"# Not found: {n}\n"
    return Response(a, content_type="text/plain")


@app.route('/mirrorSites.json')
def json_mirror_sites():
    return jsonify(mirror_sites)


if __name__ == '__main__':
    app.run()
