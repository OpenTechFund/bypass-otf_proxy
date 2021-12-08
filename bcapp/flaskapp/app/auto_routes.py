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
        # TODO GH #79 - this has to include Github
        domain = Domain.query.filter_by(id=id).first_or_404()
        db.session.delete(domain)
        db.session.commit()
        return redirect(url_for('admin_domains', status='active'))


@app.route('/admin/domains/add', methods=['GET', 'POST'])
@login_required
def new_domain():
    """
    Add New Domain
    """
    if not current_user.admin:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))
    else:
        form = DomainForm()
        if request.method == 'POST':
            form_domain = form.domain.data
            paths_ignore = form.paths_ignore.data
            ext_ignore = form.ext_ignore.data
            s3_storage_bucket = form.s3_storage_bucket.data
            azure_profile_name = form.azure_profile_name.data
            inactive = form.inactive.data
            # Does this domain exist in the database or github?
            db_check = Domain.query.filter_by(domain=form_domain).first()
            gh_check = repo_utilities.check(form_domain)
            if not gh_check['exists']: # not in GH
                # Add to Github
                added = automation.new_add(
                    domain=form_domain,
                    mode='web'
                )
                if not db_check: # not in db either
                    domain = Domain(
                        domain=form_domain,
                        paths_ignore=paths_ignore,
                        ext_ignore=ext_ignore,
                        s3_storage_bucket=s3_storage_bucket,
                        azure_profile_name=azure_profile_name,
                        inactive=inactive
                    )
                    db.session.add(domain)
                    db.session.commit()
                    flash("Domain Added!")
                else: # in db already
                    if db_check.inactive: #set to inactive
                        domain.inactive = False
                        db.session.commit()
                    flash("Domain Added, set to active again!")   
            else: # exists in GH
                if db_check: #domain exists in db
                    if db_check.inactive: #set to inactive
                        domain.inactive = False
                        db.session.commit()
                    else:
                        flash("Domain already exists!")
                        
            return redirect(url_for('admin_domains', status='active'))
        else:
            return render_template('edit_domain.html', form=form, new=True)

@app.route('/alternatives/add', methods=['GET','POST'])
@login_required
def add_alternative():
    """
    Add new alternative
    """
    if not current_user.admin:  
        flash('Have to be an admin!')
        return redirect(url_for('profile'))
    else:
        form = AltForm()
        if request.method == 'POST':
            domain_id = request.form.get('domain_id')
            domain = Domain.query.filter(Domain.id==domain_id).first_or_404()
            mirror_type = form.mirror_type.data
            mirror_url = form.mirror_url.data
            service = request.form.get('service')
            www_redirect = request.form.get('www_redirect')
            if mirror_type == 'mirror':
                protocol = 'http'
            elif mirror_type == 'eotk':
                protocol = 'tor'
            else:
                protocol = 'https'

            # is it already there?
            db_exists = False
            test_mirror = Mirror.query.filter(Mirror.mirror_url==mirror_url).first()
            if test_mirror and test_mirror.mirror_url == mirror_url:
                db_exists = True

            # github
            domain_data = repo_utilities.check(domain.domain)
            gh_exists = False
            for alt in domain_data['available_alternatives']:
                if mirror_url == alt['url']:
                    gh_exists = True

            if (gh_exists and db_exists) and not test_mirror.inactive:
                flash("Mirror Already Exists!!")
                return redirect(url_for('edit_domain', id=domain_id))

            # Add to github
            if not gh_exists:
                if mirror_type == 'proxy':
                    gh_mt = service
                elif mirror_type == 'eotk':
                    gh_mt = 'onion'
                else:
                    gh_mt = mirror_type
                added = automation.new_add(
                    domain=domain.domain,
                    mirror_type=gh_mt,
                    existing=mirror_url,
                    mode='web',
                    www_redirect=www_redirect
                )
            
            if 'failed' in added:
                flash("No Alternative added!")
                return redirect(url_for('edit_domain', id=domain_id))
            elif db_exists and test_mirror.inactive:
                test_mirror.inactive = False
                db.session.commit()
                flash("Mirror added back, made active!")
            else:
                alternative = Mirror(mirror_type=mirror_type, mirror_url=added, domain_id=domain_id, protocol=protocol, inactive=False)
                db.session.add(alternative)
                db.session.commit()
                flash('Alternative Added')

            return redirect(url_for('edit_domain', id=domain_id))
            
        else:
            form.domain_id.data = request.args.get('id')
            return render_template('edit_alternative.html', form=form)

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
        source = request.args.get('source')
        # Get Domain/Alternative info from database and repo
        mirror = Mirror.query.filter(Mirror.mirror_url==url).first_or_404()
        domain = Domain.query.filter(Domain.id==mirror.domain_id).first_or_404()
        remove = repo_utilities.remove_mirror(
            domain=domain.domain,
            remove=url
        )
        flash(remove)
        if source == 'alternatives':
            return redirect(url_for('alternatives', url=url))
        else:
            return redirect(url_for('edit_domain', id=mirror.domain_id))


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
        all_mirrors = repo_utilities.domain_listing()
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

            automated = request.form.get('automated')
            
            # Save in github
            replaced = automation.replace_mirror(mirror_type=mirror_type,
                                                domain=domain.domain,
                                                replace=form.old_url.data,
                                                existing=mirror.mirror_url,
                                                mode='web',
                                                automated=automated
                                            )
            if replaced: 
                if automated:
                    mirror.mirror_url = replaced
                #save in database
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
                                   old_url=mirror.mirror_url,
                                   existing=True)
