from datetime import datetime

import boto3 as boto3
from flask import Flask, jsonify, render_template, Response, redirect, url_for
import yaml

from app.forms import EditGroupForm, EditOriginForm, EditMirrorForm, EditProxyForm, LifecycleForm
from app.extensions import db
from app.extensions import migrate
from app.extensions import bootstrap
from app.mirror_sites import mirror_sites
from app.models import Group, Origin, Proxy, Mirror

app = Flask(__name__)
app.config.from_file("../config.yaml", load=yaml.safe_load)
db.init_app(app)
migrate.init_app(app, db)
bootstrap.init_app(app)


@app.route('/a/groups')
def json_list_groups():
    res = Group.query.all()
    return jsonify({"groups": [x.as_dict() for x in res]})


@app.route('/a/origins')
def json_list_origins():
    res = Origin.query.all()
    return jsonify({"origins": [x.as_dict() for x in res]})


@app.route('/a/mirrors')
def json_list_mirrors():
    res = Mirror.query.all()
    return jsonify({"mirrors": [x.as_dict() for x in res]})


@app.route('/a/proxies')
def json_list_proxies():
    res = Proxy.query.filter(Proxy.destroyed is None).all()
    return jsonify({"proxies": [x.as_dict() for x in res]})


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/groups')
def list_groups():
    res = Group.query.order_by(Group.group_name).all()
    return render_template("groups.html", groups=res)


@app.route('/group/<group_id>', methods=['GET', 'POST'])
def edit_group(group_id):
    group = Group.query.filter(Group.id == group_id).first()
    form = EditGroupForm(group_id=group.id, description=group.description)
    if form.validate_on_submit():
        group.description = form.description.data
        group.updated = datetime.utcnow()
        db.session.commit()
    return render_template("group.html", group=group, form=form)


@app.route('/origins')
def list_origins():
    res = Origin.query.order_by(Origin.domain_name).all()
    return render_template("origins.html", origins=res)


@app.route('/origin/<origin_id>', methods=['GET', 'POST'])
def edit_origin(origin_id):
    if origin_id == "new":
        new = True
        origin = Origin()
        origin.domain_name = "www.example.com"
        origin.description = "New origin"
        origin.created = datetime.utcnow()
        origin.group = Group.query.first()
        origin.provider = "cloudfront"
    else:
        new = False
        origin = Origin.query.filter(Origin.id == origin_id).first()
    form = EditOriginForm(domain_name=origin.domain_name, description=origin.description, group=origin.group.id)
    form.group.choices = [(x.id, x.group_name) for x in Group.query.all()]
    if form.validate_on_submit():
        origin.domain_name = form.domain_name.data
        origin.description = form.description.data
        origin.group_id = form.group.data
        origin.updated = datetime.utcnow()
        db.session.commit()
    return render_template("origin.html", origin=origin, form=form, new=new)


@app.route('/mirror/<mirror_id>', methods=['GET', 'POST'])
def edit_mirror(mirror_id):
    res = Mirror.query.filter(Mirror.id == mirror_id).first()
    form = EditMirrorForm(origin=res.origin.id, url=res.url)
    form.origin.choices = [(x.id, x.domain_name) for x in Origin.query.all()]
    if form.validate_on_submit():
        res.origin_id = form.origin.data
        res.url = form.url.data
        res.updated = datetime.utcnow()
        db.session.commit()
    return render_template("mirror.html", mirror=res, form=form)


@app.route('/mirrors')
def list_mirrors():
    res = Mirror.query.all()
    return render_template("mirrors.html", mirrors=res)


def lifecycle(alt_type, action, resource):
    form = LifecycleForm()
    if form.validate_on_submit():
        if action == "destroy":
            resource.destroyed = datetime.utcnow()
        if action == "restore":
            resource.deprecated = None
        if action == "deprecate":
            resource.deprecated = datetime.utcnow()
        db.session.commit()
        return redirect(url_for("edit_origin", origin_id=resource.origin.id))
    if action == "restore":
        form.submit.render_kw = {'class': "btn btn-success"}
    if action == "deprecate":
        form.submit.render_kw = {'class': "btn btn-warning"}
    if action == "destroy":
        form.submit.render_kw = {'class': "btn btn-danger"}
    return render_template("lifecycle.html",
                           form=form,
                           type=alt_type,
                           action=action,
                           resource=resource)


@app.route('/proxy/<action>/<proxy_id>', methods=['GET', 'POST'])
def lifecycle_proxy(action, proxy_id):
    proxy = Proxy.query.filter(Proxy.id == proxy_id).first()
    return lifecycle("proxy", action, proxy)


@app.route('/proxy/<action>/<mirror_id>', methods=['GET', 'POST'])
def lifecycle_mirror(action, mirror_id):
    mirror = Mirror.query.filter(Mirror.id == mirror_id).first()
    return lifecycle("mirror", action, mirror)


@app.route('/proxy/<proxy_id>', methods=['GET', 'POST'])
def edit_proxy(proxy_id):
    if proxy_id == "new":
        new = True
        proxy = Proxy()
        proxy.created = datetime.utcnow()
        proxy.origin = Origin.query.first()
        proxy.provider = "cloudfront"
    else:
        new = False
        proxy = Proxy.query.filter(Proxy.id == proxy_id).first()
    form = EditProxyForm(origin=proxy.origin.id)
    form.origin.choices = [(x.id, x.domain_name) for x in Origin.query.all()]
    if form.validate_on_submit():
        proxy.origin_id = form.origin.data
        proxy.updated = datetime.utcnow()
        db.session.commit()
        return redirect(url_for("edit_proxy", proxy_id=proxy.id))
    return render_template("proxy.html", proxy=proxy, form=form, new=new)


@app.route('/proxies')
def list_proxies():
    res = Proxy.query.order_by('url').filter(Proxy.destroyed == None).all()
    return render_template("proxies.html", proxies=res)


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
