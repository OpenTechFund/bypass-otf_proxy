import datetime
from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import app
from app.models import User, Token, Domain, Mirror, Report, LogReport, DomainGroup, DGDomain
from app.forms import UserForm, DomainForm, DomainGroupForm, AltForm
from . import db
from . import admin_utilities
import repo_utilities
import automation

"""
Automation Routes - adding automation functions to Web interface
"""

@app.route('/alternatives/add')
@login_required
def add_alternative():
    """
    Add new alternative
    """
    pass

@app.route('/alternatives/remove', methods=['GET'])
@login_required
def remove_alternative():
    """
    Remove alternative 
    """
    if not current_user.admin:  
        flash('Have to be an admin!')
        return redirect(url_for('profile'))
    else:
        url = request.args.get('url')
        # Get Domain/Alternative info from database and repo
        mirror = Mirror.query.filter(Mirror.mirror_url==url).first_or_404()
        print(f"Mirror: {mirror.id} Domain: {mirror.domain_id}")
        domain = Domain.query.filter(Domain.id==mirror.domain_id).first_or_404()
        print(f"Domain: {domain.domain}")
        remove = repo_utilities.remove_mirror(
            domain=domain.domain,
            remove=url,
            nogithub=False
        )
        flash(remove)
        return redirect(url_for('alternatives', url=url))


@app.route('/alternatives/edit',  methods=['GET', 'POST'])
@login_required
def edit_alternative():
    """
    Edit alternative
    """
    if not current_user.admin:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))
    else:
        url = request.args.get('url')
        # Get Domain/Alternative info from database and repo
        mirror = Mirror.query.filter(Mirror.mirror_url==url).first_or_404()
        domain = Domain.query.filter(Domain.id==mirror.domain_id).first_or_404()
        all_mirrors = repo_utilities.domain_list()
        form = AltForm()

        if '.onion' in mirror.mirror_url:
            m_type = 'eotk'
            m_pro = 'tor'
            mirror_type = 'onion'
        elif 'cloudfront' in mirror.mirror_url:
            m_type = 'proxy'
            m_pro = 'https'
            mirror_type = 'cloudfront'
        elif 'fastly' in mirror.mirror_url:
            m_type = 'proxy'
            m_pro = 'https'
            mirror_type = 'fastly'
        elif 'azureedge' in mirror.mirror_url:
            m_type = 'proxy'
            m_pro = 'https'
            mirror_type = 'azure'
        elif 'ipfs' in mirror.mirror_url:
            m_type = 'ipfs'
            m_pro = 'https'
            mirror_type = 'ipfs'
        else:
            m_type = 'mirror'
            m_pro = 'http'
            mirror_type = 'mirror'

        if request.method == 'POST':
            # Manual first. Programmatic TODO
            mirror.mirror_url = form.mirror_url.data
            mirror.mirror_type = form.mirror_type.data
            mirror.inactive = form.inactive.data
            mirror.mirror_type = m_type
            mirror.protocol = m_pro
            if form.mirror_type.data == 'eotk':
                mirror.protocol = 'tor'
            elif form.mirror_type.data == 'mirror':
                mirror.protocol = 'http'
            else:
                mirror.protocol = 'https'

            
            # Save in github
            replaced = automation.replace_mirror(mirror_type=mirror_type,
                                                domain=domain.domain,
                                                replace=form.old_url.data,
                                                existing=mirror.mirror_url,
                                                mode='web'
                                            )
            if replaced: #save in database
                db.session.commit()
                flash('Your changes have been saved.')
            
            return redirect(url_for('alternatives', domain_choice=domain.domain))

        else:
            form.mirror_url.data = mirror.mirror_url
            form.old_url.data = mirror.mirror_url
            if mirror.mirror_type:
                form.mirror_type.data = mirror.mirror_type
            else:
                form.mirror_type.data = m_type
            form.inactive.data = mirror.inactive

            return render_template('edit_alternative.html',
                                   title=f"Edit Alternative for {domain.domain}",
                                   mirror=mirror,
                                   form=form,
                                   old_url=mirror.mirror_url)
