import datetime
from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import app
from app.models import User, Token, Domain, Mirror, Report, LogReport, DomainGroup
from app.forms import UserForm, DomainForm
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
        return render_template('admin_domains.html', domains=domains)

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
            db.session.commit()
            flash('Your changes have been saved.')
            return redirect(url_for('admin_domains'))
        elif request.method == 'GET':
            form.domain.data = domain.domain
            form.ext_ignore.data = domain.ext_ignore
            form.paths_ignore.data = domain.paths_ignore
            form.s3_storage_bucket.data = domain.s3_storage_bucket
            
        return render_template('edit_domain.html',
                                    title='Edit Doman',
                                    domain=domain,
                                    form=form)


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
        return render_template('admin_domain_groups.html')

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
            form.domain_group_id.choices = [(dg.id, dg.name) for dg in DomainGroup.query.order_by('name').all()]
            form.domain_group_id.data = user.domain_group_id
        return render_template('edit_user.html',
                                title='Edit User',
                                user=user,
                                form=form)

@app.route('/testing', methods=['GET'])
@login_required
def testing():
    """
    Domain and other tests
    """
    if not current_user.admin:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))
    else:
        domain_list = Domain.query.all()
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
    if not current_user.admin:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))
    else:
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


@app.route('/reports')
@login_required
def reports():
    """
    Reports
    """
    if current_user.admin:
        domain_list = Domain.query.all()
        domains = []
        for dom in domain_list:
            domains.append(dom.domain)
        report_types = [
            #{
            #   'name': 'Log Reports List',
            #   'report': 'log_reports_list'
            #},
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
    else:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))

@app.route('/admin/log_reports')
@login_required
def log_reports_list():
    if current_user.admin:
        log_reports = admin_utilities.log_report_list()
        return render_template('log_reports_list.html', name=current_user.name, log_reports=log_reports)
    else:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))

@app.route('/admin/domain_reports', methods=['GET'])
@login_required
def recent_domain_reports():
    domain_choice = request.args.get('domain_choice')
    if current_user.admin:
        print(f"Domain choice: {domain_choice}")
        recent_reports = admin_utilities.get_recent_domain_reports(domain_choice)
        return render_template('recent_domain_reports.html', name=current_user.name, recent_reports=recent_reports, domain_choice=domain_choice)
    else:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))

@app.route('/admin/bad_domains')
@login_required
def bad_domains():
    if current_user.admin:
        bad_domains = admin_utilities.bad_domains()
        if not bad_domains:
            all_good = True
        else:
            all_good = False
        return render_template('bad_domains.html', name=current_user.name, bad_domains=bad_domains, all_good=all_good)
    else:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))

@app.route('/admin/bad_mirrors')
@login_required
def bad_mirrors():
    if current_user.admin:
        bad_mirrors = admin_utilities.bad_mirrors()
        return render_template('bad_mirrors.html', name=current_user.name, bad_mirrors=bad_mirrors)
    else:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))

@app.route('/admin/monthy_bad')
@login_required
def monthly_bad():
    if current_user.admin:
        monthly_bad = admin_utilities.monthly_bad()
        return render_template('monthly_bad.html', name=current_user.name, monthly_bad=monthly_bad)
    else:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))

## Log Reports
@app.route('/log_reports/display', methods=['GET'])
@login_required
def display_log_report():
    """
    List one report
    """
    # grab report
    log_report_id = request.args.get('id')
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
