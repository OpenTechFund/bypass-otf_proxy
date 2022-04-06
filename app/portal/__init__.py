from datetime import datetime, timedelta

from flask import Blueprint, render_template, Response, flash, redirect, url_for, request
from sqlalchemy import exc, desc, or_

from app.extensions import db
from app.models import Group, Origin, Proxy, Alarm, BridgeConf, Bridge, MirrorList
from app.portal.forms import EditGroupForm, NewGroupForm, NewOriginForm, EditOriginForm, LifecycleForm, \
    NewBridgeConfForm, EditBridgeConfForm, NewMirrorListForm

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
            return redirect(url_for("portal.edit_origin", origin_id=origin.id))
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
                          description=origin.description)
    form.group.choices = [(x.id, x.group_name) for x in Group.query.all()]
    if form.validate_on_submit():
        origin.group_id = form.group.data
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
    mirrorlists = MirrorList.query.filter(MirrorList.destroyed == None).all()
    return render_template("mirrorlists.html.j2", section="list", mirrorlists=mirrorlists)


@portal.route("/list/destroy/<list_id>")
def destroy_mirror_list(list_id):
    return "not implemented"

@portal.route("/list/new", methods=['GET', 'POST'])
@portal.route("/list/new/<group_id>", methods=['GET', 'POST'])
def new_mirror_list(group_id=None):
    form = NewMirrorListForm()
    form.provider.choices = [
        ("github", "GitHub"),
        ("gitlab", "GitLab"),
        ("s3", "AWS S3"),
    ]
    form.format.choices = [
        ("bc2", "Bypass Censorship v2"),
        ("bc3", "Bypass Censorship v3"),
        ("bca", "Bypass Censorship Analytics"),
        ("bridgelines", "Tor Bridge Lines")
    ]
    form.container.description = "GitHub Project, GitLab Project or AWS S3 bucket name."
    form.branch.description = "Ignored for AWS S3."
    if form.validate_on_submit():
        mirror_list = MirrorList()
        mirror_list.provider = form.provider.data
        mirror_list.format = form.format.data
        mirror_list.description = form.description.data
        mirror_list.container = form.container.data
        mirror_list.branch = form.branch.data
        mirror_list.filename = form.filename.data
        mirror_list.created = datetime.utcnow()
        mirror_list.updated = datetime.utcnow()
        try:
            db.session.add(mirror_list)
            db.session.commit()
            flash(f"Created new mirror list.", "success")
            return redirect(url_for("portal.view_mirror_lists"))
        except exc.SQLAlchemyError as e:
            print(e)
            flash("Failed to create new mirror list.", "danger")
            return redirect(url_for("portal.view_mirror_lists"))
    if group_id:
        form.group.data = group_id
    return render_template("new.html.j2", section="list", form=form)


@portal.route("/bridgeconfs")
def view_bridgeconfs():
    bridgeconfs = BridgeConf.query.filter(BridgeConf.destroyed == None).all()
    return render_template("bridgeconfs.html.j2", section="bridgeconf", bridgeconfs=bridgeconfs)


@portal.route("/bridgeconf/new", methods=['GET', 'POST'])
@portal.route("/bridgeconf/new/<group_id>", methods=['GET', 'POST'])
def new_bridgeconf(group_id=None):
    form = NewBridgeConfForm()
    form.group.choices = [(x.id, x.group_name) for x in Group.query.all()]
    form.provider.choices = [
        ("aws", "AWS Lightsail"),
        ("hcloud", "Hetzner Cloud"),
        ("ovh", "OVH Public Cloud"),
        ("gandi", "GandiCloud VPS")
    ]
    form.method.choices = [
        ("any", "Any (BridgeDB)"),
        ("email", "E-Mail (BridgeDB)"),
        ("moat", "Moat (BridgeDB)"),
        ("https", "HTTPS (BridgeDB)"),
        ("none", "None (Private)")
    ]
    if form.validate_on_submit():
        bridge_conf = BridgeConf()
        bridge_conf.group_id = form.group.data
        bridge_conf.provider = form.provider.data
        bridge_conf.method = form.method.data
        bridge_conf.description = form.description.data
        bridge_conf.number = form.number.data
        bridge_conf.created = datetime.utcnow()
        bridge_conf.updated = datetime.utcnow()
        try:
            db.session.add(bridge_conf)
            db.session.commit()
            flash(f"Created new bridge configuration {bridge_conf.id}.", "success")
            return redirect(url_for("portal.view_bridgeconfs"))
        except exc.SQLAlchemyError as e:
            print(e)
            flash("Failed to create new bridge configuration.", "danger")
            return redirect(url_for("portal.view_bridgeconfs"))
    if group_id:
        form.group.data = group_id
    return render_template("new.html.j2", section="bridgeconf", form=form)


@portal.route("/bridges")
def view_bridges():
    bridges = Bridge.query.filter(Bridge.destroyed == None).all()
    return render_template("bridges.html.j2", section="bridge", bridges=bridges)


@portal.route('/bridgeconf/edit/<bridgeconf_id>', methods=['GET', 'POST'])
def edit_bridgeconf(bridgeconf_id):
    bridgeconf = BridgeConf.query.filter(BridgeConf.id == bridgeconf_id).first()
    if bridgeconf is None:
        return Response(render_template("error.html.j2",
                                        section="origin",
                                        header="404 Origin Not Found",
                                        message="The requested origin could not be found."),
                        status=404)
    form = EditBridgeConfForm(description=bridgeconf.description,
                              number=bridgeconf.number)
    if form.validate_on_submit():
        bridgeconf.description = form.description.data
        bridgeconf.number = form.number.data
        bridgeconf.updated = datetime.utcnow()
        try:
            db.session.commit()
            flash("Saved changes to bridge configuration.", "success")
        except exc.SQLAlchemyError:
            flash("An error occurred saving the changes to the bridge configuration.", "danger")
    return render_template("bridgeconf.html.j2",
                           section="bridgeconf",
                           bridgeconf=bridgeconf, form=form)


@portal.route("/bridge/block/<bridge_id>", methods=['GET', 'POST'])
def blocked_bridge(bridge_id):
    bridge = Bridge.query.filter(Bridge.id == bridge_id, Bridge.destroyed == None).first()
    if bridge is None:
        return Response(render_template("error.html.j2",
                                        header="404 Proxy Not Found",
                                        message="The requested bridge could not be found."))
    form = LifecycleForm()
    if form.validate_on_submit():
        bridge.deprecate()
        flash("Bridge will be shortly replaced.", "success")
        return redirect(url_for("portal.edit_bridgeconf", bridgeconf_id=bridge.conf_id))
    return render_template("blocked.html.j2",
                           header=f"Mark bridge {bridge.hashed_fingerprint} as blocked?",
                           message=bridge.hashed_fingerprint,
                           section="bridge",
                           form=form)


@portal.route("/bridgeconf/destroy/<bridgeconf_id>", methods=['GET', 'POST'])
def destroy_bridgeconf(bridgeconf_id):
    bridgeconf = BridgeConf.query.filter(BridgeConf.id == bridgeconf_id, BridgeConf.destroyed == None).first()
    if bridgeconf is None:
        return Response(render_template("error.html.j2",
                                        header="404 Proxy Not Found",
                                        message="The requested bridge configuration could not be found."))
    form = LifecycleForm()
    if form.validate_on_submit():
        bridgeconf.destroy()
        flash("All bridges from the destroyed configuration will shortly be destroyed at their providers.", "success")
        return redirect(url_for("portal.view_bridgeconfs"))
    return render_template("blocked.html.j2",
                           header=f"Destroy?",
                           message=bridgeconf.description,
                           section="bridgeconf",
                           form=form)

