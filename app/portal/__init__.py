from datetime import datetime, timedelta

import boto3
from flask import Blueprint, render_template, Response, flash, redirect, url_for, request, current_app
from sqlalchemy import exc, desc, or_

from app.extensions import db
from app.models import Group, Origin, Proxy, Alarm
from app.portal.forms import EditGroupForm, NewGroupForm, NewOriginForm, EditOriginForm, LifecycleForm

portal = Blueprint("portal", __name__, template_folder="templates", static_folder="static")


@portal.app_template_filter("mirror_expiry")
def calculate_mirror_expiry(s):
    expiry = s + timedelta(days=3)
    countdown = expiry - datetime.utcnow()
    if countdown.days == 0:
        return f"{countdown.seconds // 3600} hours"
    return f"{countdown.days} days"


@portal.route("/")
def portal_home():
    return render_template("home.html.j2", section="home")


@portal.route("/groups")
def view_groups():
    groups = Group.query.order_by(Group.group_name).all()
    return render_template("groups.html.j2", section="group", groups=groups)


@portal.route("/group/new", methods=['GET', 'POST'])
def new_group():
    form = NewGroupForm()
    if form.validate_on_submit():
        group = Group()
        group.group_name = form.group_name.data
        group.description = form.description.data
        group.eotk = form.eotk.data
        group.created = datetime.utcnow()
        group.updated = datetime.utcnow()
        try:
            db.session.add(group)
            db.session.commit()
            flash(f"Created new group {group.group_name}.", "success")
            return redirect(url_for("portal.edit_group", group_id=group.id))
        except exc.SQLAlchemyError as e:
            print(e)
            flash("Failed to create new group.", "danger")
            return redirect(url_for("portal.view_groups"))
    return render_template("new.html.j2", section="group", form=form)


@portal.route('/group/edit/<group_id>', methods=['GET', 'POST'])
def edit_group(group_id):
    group = Group.query.filter(Group.id == group_id).first()
    if group is None:
        return Response(render_template("error.html.j2",
                                        section="group",
                                        header="404 Group Not Found",
                                        message="The requested group could not be found."),
                        status=404)
    form = EditGroupForm(description=group.description,
                         eotk=group.eotk)
    if form.validate_on_submit():
        group.description = form.description.data
        group.eotk = form.eotk.data
        group.updated = datetime.utcnow()
        try:
            db.session.commit()
            flash("Saved changes to group.", "success")
        except exc.SQLAlchemyError:
            flash("An error occurred saving the changes to the group.", "danger")
    return render_template("group.html.j2",
                           section="group",
                           group=group, form=form)


@portal.route("/origin/new", methods=['GET', 'POST'])
@portal.route("/origin/new/<group_id>", methods=['GET', 'POST'])
def new_origin(group_id=None):
    form = NewOriginForm()
    form.group.choices = [(x.id, x.group_name) for x in Group.query.all()]
    if form.validate_on_submit():
        origin = Origin()
        origin.group_id = form.group.data
        origin.domain_name = form.domain_name.data
        origin.description = form.description.data
        origin.created = datetime.utcnow()
        origin.updated = datetime.utcnow()
        try:
            db.session.add(origin)
            db.session.commit()
            flash(f"Created new origin {origin.domain_name}.", "success")
            return redirect(url_for("portal.edit_origin", group_id=origin.id))
        except exc.SQLAlchemyError as e:
            print(e)
            flash("Failed to create new origin.", "danger")
            return redirect(url_for("portal.view_origins"))
    if group_id:
        form.group.data = group_id
    return render_template("new.html.j2", section="origin", form=form)


@portal.route('/origin/edit/<origin_id>', methods=['GET', 'POST'])
def edit_origin(origin_id):
    origin = Origin.query.filter(Origin.id == origin_id).first()
    if origin is None:
        return Response(render_template("error.html.j2",
                                        section="origin",
                                        header="404 Origin Not Found",
                                        message="The requested origin could not be found."),
                        status=404)
    form = EditOriginForm(group=origin.group_id,
                          domain_name=origin.domain_name,
                          description=origin.description)
    form.group.choices = [(x.id, x.group_name) for x in Group.query.all()]
    if form.validate_on_submit():
        origin.group_id = form.group.data
        origin.domain_name = form.domain_name.data
        origin.description = form.description.data
        origin.updated = datetime.utcnow()
        try:
            db.session.commit()
            flash("Saved changes to group.", "success")
        except exc.SQLAlchemyError:
            flash("An error occurred saving the changes to the group.", "danger")
    return render_template("origin.html.j2",
                           section="origin",
                           origin=origin, form=form)


@portal.route("/origins")
def view_origins():
    origins = Origin.query.order_by(Origin.domain_name).all()
    return render_template("origins.html.j2", section="origin", origins=origins)


@portal.route("/proxies")
def view_proxies():
    proxies = Proxy.query.filter(Proxy.destroyed == None).order_by(desc(Proxy.updated)).all()
    return render_template("proxies.html.j2", section="proxy", proxies=proxies)


@portal.route("/proxy/block/<proxy_id>", methods=['GET', 'POST'])
def blocked_proxy(proxy_id):
    proxy = Proxy.query.filter(Proxy.id == proxy_id, Proxy.destroyed == None).first()
    if proxy is None:
        return Response(render_template("error.html.j2",
                                        header="404 Proxy Not Found",
                                        message="The requested proxy could not be found."))
    form = LifecycleForm()
    if form.validate_on_submit():
        proxy.deprecate()
        flash("Proxy will be shortly replaced.", "success")
        return redirect(url_for("portal.edit_origin", origin_id=proxy.origin.id))
    return render_template("blocked.html.j2",
                           header=f"Mark proxy for {proxy.origin.domain_name} as blocked?",
                           message=proxy.url,
                           section="proxy",
                           form=form)


@portal.route("/search")
def search():
    query = request.args.get("query")
    proxies = Proxy.query.filter(or_(Proxy.url.contains(query)), Proxy.destroyed == None).all()
    origins = Origin.query.filter(or_(Origin.description.contains(query), Origin.domain_name.contains(query))).all()
    return render_template("search.html.j2", section="home", proxies=proxies, origins=origins)


@portal.route('/alarms')
def view_alarms():
    alarms = Alarm.query.order_by(Alarm.alarm_state, desc(Alarm.state_changed)).all()
    return render_template("alarms.html.j2", section="alarm", alarms=alarms)


@portal.route('/lists')
def view_mirror_lists():
    return "not implemented"