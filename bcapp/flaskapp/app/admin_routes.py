import datetime
from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import app
from app.models import User, Token, Domain, Mirror, Report, LogReport, DomainGroup, DGDomain
from app.forms import UserForm, DomainForm, DomainGroupForm
from . import db
from . import admin_utilities
import repo_utilities
import mirror_tests

### Admin

@app.route('/admin')
@login_required
def admin():
    """
    Administration
    """
    if not current_user.admin:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))
    else:
        return render_template('admin.html', name=current_user.name)

## Admin Domains/Groups

@app.route('/admin/domains')
@login_required
def admin_domains():
    """
    Administer Domains
    """
    if not current_user.admin:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))
    else:
        domains = Domain.query.all()
        dg_domains = DGDomain.query.all()
        domain_groups = DomainGroup.query.all()
        dg_dict = {}
        for dg in domain_groups:
            dg_dict[dg.id] = dg.name
        for domain in domains:
            for dgd in dg_domains:
                if dgd.domain_id == domain.id:
                    domain.coded_dg = dg_dict[dgd.domain_group_id]
                    
        return render_template('admin_domains.html', domains=domains, domain_groups=domain_groups)

@app.route('/admin/domains/domain_group_choice', methods=['GET'])
@login_required
def domain_group_choice():
    """
    Add domain group to domain
    """
    if not current_user.admin:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))
    else:
        if request.args.get('domain_group_choice'): 
            dg_domain = DGDomain(
                domain_id=request.args.get('domain_id'),
                domain_group_id=request.args.get('domain_group_choice')
            )
            db.session.add(dg_domain)
            db.session.commit()
        return redirect(url_for('admin_domains'))

@app.route('/admin/domains/<id>', methods=['GET', 'POST'])
@login_required
def edit_domain(id):
    """
    Edit a domain
    """
    if not current_user.admin:
        flash('Have to be admin')
        return redirect(url_for('home'))
    else:
        domain = Domain.query.filter_by(id=id).first_or_404()
        form = DomainForm()
        if request.method == 'POST':
            domain.domain = form.domain.data
            domain.ext_ignore = form.ext_ignore.data
            domain.paths_ignore = form.paths_ignore.data
            domain.s3_storage_bucket = form.s3_storage_bucket.data
            domain.azure_profile_name = form.azure_profile_name.data
            db.session.commit()
            flash('Your changes have been saved.')
            return redirect(url_for('admin_domains'))
        elif request.method == 'GET':
            form.domain.data = domain.domain
            form.ext_ignore.data = domain.ext_ignore
            form.paths_ignore.data = domain.paths_ignore
            form.s3_storage_bucket.data = domain.s3_storage_bucket
            form.azure_profile_name.data = domain.azure_profile_name
            
        return render_template('edit_domain.html',
                                    title='Edit Domain',
                                    domain=domain,
                                    form=form)

@app.route('/admin/domains/delete/<id>')
@login_required
def delete_domain(id):
    """
    Delete domain
    """
    if not current_user.admin:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))
    else:
        domain = Domain.query.filter_by(id=id).first_or_404()
        db.session.delete(domain)
        db.session.commit()
        return redirect(url_for('admin_domains'))

@app.route('/admin/domain_groups')
@login_required
def admin_domain_groups():
    """
    Administer Domain Groups
    """
    if not current_user.admin:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))
    else:
        domain_groups = DomainGroup.query.all()
        return render_template('admin_domain_groups.html', domain_groups=domain_groups)

@app.route('/admin/domain_groups/delete/<id>')
@login_required
def delete_domain_group(id):
    """
    Delete Domain Group
    """
    if not current_user.admin:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))
    else:
        domain_group = DomainGroup.query.filter_by(id=id).first_or_404()
        db.session.delete(domain_group)
        db.session.commit()
        return redirect(url_for('admin_domain_groups'))

@app.route('/admin/domain_groups/<id>', methods=['GET', 'POST'])
@login_required
def edit_domain_group(id):
    """
    Edit Domain Group
    """
    no_domain_group = DomainGroup.query.filter_by(name='None').first_or_404()
    if current_user.domain_group_id == str(no_domain_group.id): # bump them
        flash("Can't edit!")
        return redirect(url_for('profile'))
    elif ((current_user.admin) or (current_user.domain_group_id == str(id))):
        domain_group = DomainGroup.query.filter_by(id=id).first_or_404()
        form = DomainGroupForm()
        if request.method == 'POST':
            domain_group.name = form.name.data
            domain_group.notes = form.notes.data
            db.session.commit()
            flash('Your changes have been saved.')
            return redirect(url_for('admin_domain_groups'))
        elif request.method == 'GET':
            form.name.data = domain_group.name
            form.notes.data = domain_group.notes
        
        return render_template('edit_domain_group.html',
                                    title='Edit Domain Group',
                                    domain_group=domain_group,
                                    form=form)
    else:
        flash('Have to have permission!')
        return redirect(url_for('profile'))
        

@app.route('/admin/domain_groups/add', methods=['GET', 'POST'])
@login_required
def add_domain_group():
    """
    Add domain groups
    """
    if not current_user.admin:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))
    else:
        form = DomainGroupForm()
        if request.method == 'POST':
            name = form.name.data
            notes = form.notes.data
            domain_group = DomainGroup(name=name, notes=notes) 
            db.session.add(domain_group)
            db.session.commit()
            return redirect(url_for('admin_domain_groups'))

        return render_template('edit_domain_group.html', title="Add Domain Group", form=form)
        
## Admin Users

@app.route('/admin/users')
@login_required
def admin_users():
    """
    Administer Users
    """
    if not current_user.admin:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))
    else:
        users = User.query.all()
        return render_template('admin_users.html', users=users)

@app.route('/admin/users/delete/<id>')
@login_required
def delete_user(id):
    """
    Delete User
    """
    if not current_user.admin:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))
    else:
        user = User.query.filter_by(id=id).first_or_404()
        db.session.delete(user)
        db.session.commit()
        return redirect(url_for('admin_users'))

@app.route('/admin/users/add',  methods=['GET', 'POST'])
@login_required
def add_user():
    """
    Add user
    """
    if not current_user.admin:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))
    else:
        form = UserForm()
        if request.method == 'POST':
            name = form.name.data
            active = form.active.data
            email = form.email.data
            admin = form.admin.data
            notifications = form.notifications.data
            domain_group_id = form.domain_group_id.data
            user = User(
                name=name,
                email=email,
                active=active,
                admin=admin,
                notifications = notifications,
                domain_group_id=domain_group_id
            )
            if form.password.data:
                user.password = generate_password_hash(form.password.data)
            db.session.add(user)
            db.session.commit()
            return redirect(url_for('admin_users'))

        form.domain_group_id.choices = [(dg.id, dg.name) for dg in DomainGroup.query.order_by('name').all()]
        return render_template('edit_user.html', title="Add User", form=form)


@app.route('/admin/users/<id>', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    if not current_user.admin:
        flash('Have to be admin')
        return redirect(url_for('home'))
    else:
        user = User.query.filter_by(id=id).first_or_404()
        form = UserForm()
        if request.method == 'POST':
            user.admin = form.admin.data
            user.active = form.active.data
            user.email = form.email.data
            user.notifications = form.notifications.data
            if form.password.data:
                user.password = generate_password_hash(form.password.data)
            user.name = form.name.data
            user.domain_group_id = form.domain_group_id.data
            db.session.commit()
            flash('Your changes have been saved.')
            return redirect(url_for('admin_users'))
        elif request.method == 'GET':
            form.admin.data = user.admin
            form.active.data = user.active
            form.email.data = user.email
            form.name.data = user.name
            form.notifications.data = user.notifications
            form.domain_group_id.choices = [(dg.id, dg.name) for dg in DomainGroup.query.order_by('name').all()]
            form.domain_group_id.data = user.domain_group_id
        return render_template('edit_user.html',
                                title='Edit User',
                                user=user,
                                form=form)

## Testing

@app.route('/testing', methods=['GET'])
@login_required
def testing():
    """
    Domain and other tests
    """   
    if current_user.admin:
        domain_list = Domain.query.all()
    else:
        domain_list = admin_utilities.get_domain_subset(current_user.domain_group_id)

    domains = []
    for dom in domain_list:
        domains.append(dom.domain)
    if request.args.get('url'):
        url = request.args.get('url')
        if '.onion' in url:
            status, final_url = mirror_tests.test_onion(url, 'web')
        else:
            status, final_url = mirror_tests.test_domain(url, '', 'web', '')
    else:
        status, final_url = False, False

    return render_template('testing.html', name=current_user.name, status=status, final_url=final_url, domains=domains)

@app.route('/testing/alternatives', methods=['GET'])
@login_required
def alternatives():
    """
    Get alternatives from GitHub
    """
    if request.args.get('url'):
        url = request.args.get('url')
        if '.onion' in url:
            status, final_url = mirror_tests.test_onion(url, 'web')
            if status != 200:
                result = 'down'
            else:
                result = 'up'
        else:
            status, final_url = mirror_tests.test_domain(url, '', 'web', '')
            if status != 200:
                result = 'down'
            else:
                result = 'up'
    else:
        url = False
        result = 'none'
    domain_choice = request.args.get('domain_choice')
    alternatives_list = repo_utilities.check(domain_choice)
    if not alternatives_list['exists']:
        alternatives = False
    else:
        alternatives = alternatives_list['available_alternatives']
    return render_template('alternatives.html', domain_choice=domain_choice, alternatives=alternatives, url=url, result=result)

## Reporting

## Log Reporting

@app.route('/log_reports')
@login_required
def log_reports():
    """
    Log reporting
    """
    if current_user.admin:
        domain_list = Domain.query.all()
    else:
        domain_list = admin_utilities.get_domain_subset(current_user.domain_group_id)

    domains = []
    for dom in domain_list:
        if dom.s3_storage_bucket:
            domains.append(dom.domain)
    return render_template('log_reports.html', name=current_user.name, domains=domains)


@app.route('/admin/log_reports')
@login_required
def log_reports_list():
    domain_choice = request.args.get('domain_choice')
    log_reports = admin_utilities.list_log_reports(domain_choice)
    return render_template('log_reports_list.html', name=current_user.name, log_reports=log_reports, domain=domain_choice)
   

@app.route('/log_reports/domain', methods=['GET'])
@login_required
def domain_log_report():
    """
    Log report for a specific domain
    """
    domain_list = Domain.query.all()
    # grab report
    domain_choice = request.args.get('domain_choice')
    log_report = LogReport.query.filter_by(id=log_report_id).first()
    domain_name = Domain.query.filter_by(id=log_report.domain_id).first().domain
    if not log_report:
        flash('No such report!')
        return redirect(url_for('admin'))
    if current_user.admin or int(current_user.domain_id) == int(log_report.domain_id):
        report_text = log_report.report.split('\n')
        return render_template('log_report.html', log_report=log_report, domain=domain_name, report_text=report_text)
    else:
        flash("Don't have access to that domain!!")
        return redirect(url_for('profile'))

## Domain Reporting
@app.route('/reports')
@login_required
def reports():
    """
    Reports
    """
    if current_user.admin:
        domain_list = Domain.query.all()
    else:
        domain_list = admin_utilities.get_domain_subset(current_user.domain_group_id)

    domains = []
    for dom in domain_list:
        domains.append(dom.domain)
    report_types = [
        {
            'name': 'Recent Domain Reports',
            'report': 'recent_domain_reports'
        },
        {
            'name': "Last Week's Bad Domains",
            'report': 'bad_domains'
        },
        {
            'name': "Last Week's Bad Mirrors",
            'report': 'bad_mirrors'
        },
        {
            'name': "Monthly Aggregate Report",
            'report': 'monthly_bad'
        }
    ]
    return render_template('reports.html', name=current_user.name, report_types=report_types, domains=domains)


@app.route('/admin/domain_reports', methods=['GET'])
@login_required
def recent_domain_reports():
    domain_choice = request.args.get('domain_choice')
    if current_user.admin:
        auth = True
    else:
        auth = admin_utilities.auth_user(current_user.domain_group_id, domain_choice)

    if auth:
        recent_reports = admin_utilities.get_recent_domain_reports(domain_choice)
        return render_template('recent_domain_reports.html', name=current_user.name, recent_reports=recent_reports, domain_choice=domain_choice)
    else:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))

@app.route('/admin/bad_domains')
@login_required
def bad_domains():
    bad_domains = admin_utilities.bad_domains(current_user.admin, current_user.domain_group_id)
    if not bad_domains:
        all_good = True
    else:
        all_good = False
    return render_template('bad_domains.html', name=current_user.name, bad_domains=bad_domains, all_good=all_good)

@app.route('/admin/bad_mirrors')
@login_required
def bad_mirrors():
    bad_mirrors = admin_utilities.bad_mirrors(current_user.admin, current_user.domain_group_id)
    return render_template('bad_mirrors.html', name=current_user.name, bad_mirrors=bad_mirrors)

@app.route('/admin/monthy_bad')
@login_required
def monthly_bad():
    monthly_bad = admin_utilities.monthly_bad(current_user.admin, current_user.domain_group_id)
    return render_template('monthly_bad.html', name=current_user.name, monthly_bad=monthly_bad)
    
    
### Domain Group User Admin

@app.route('/domain_group/admin')
@login_required
def domain_group_admin():
    """
    Admin page for domain groups
    """
    no_domain_group = DomainGroup.query.filter_by(name='None').first_or_404()
    print(f"No: {no_domain_group} {type(current_user.domain_group_id)} {type(no_domain_group.id)}" )
    if current_user.domain_group_id == str(no_domain_group.id): # bump them
        flash("No Domains!")
        return redirect(url_for('profile'))
    else:
        return render_template('domain_group_admin.html', name=current_user.name, domain_group_id=current_user.domain_group_id)

