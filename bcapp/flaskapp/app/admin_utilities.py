import datetime
import logging
from app import app
from app.models import User, Token, Domain, Mirror, Report, LogReport, DGDomain
from sqlalchemy import desc
from . import db

logger = logging.getLogger('logger')

def list_log_reports(domain):
    """
    Generate list of log reports
    """
    domains = get_domain_list(False)
    log_reports_list = LogReport.query.order_by(LogReport.first_date_of_log.desc()).all()
    log_reports = []
    for rpt in log_reports_list:
        if domains[rpt.domain_id] == domain:
            log_report = {
                'id':rpt.id,
                'domain':domain,
                'log_type':rpt.log_type,
                'date':rpt.date_of_report,
                'report_text':rpt.report,
                'first_date':rpt.first_date_of_log,
                'last_date':rpt.last_date_of_log,
                'hits':rpt.hits
            }
            log_reports.append(log_report)
        logger.debug(log_reports)
    return log_reports

def get_domain_list(dg_id):
    """
    Generate list of domains
    """
    domains = {}
    if not dg_id:
        domains_list = Domain.query.all()
    else:
        domains_list = []
        initial_domain_list = Domain.query.all()
        domain_groups = DGDomain.query.filter_by(domain_group_id=dg_id).all()
        for dom in initial_domain_list:
            for dg in domain_groups:
                if dg.domain_id == dom.id:
                    domains_list.append(dom)

    for dom in domains_list:
        domains[dom.id] = dom.domain
    return domains

def mirror_list(dg_id):
    """
    Generate list of mirrors
    """
    mirrors = {}
    if not dg_id:
        mirrors_list = Mirror.query.all()
    else:
        mirrors_list = []
        initial_mirrors_list = Mirror.query.all()
        domain_groups = DGDomain.query.filter_by(domain_group_id=dg_id).all()
        for mir in initial_mirrors_list:
            for dg in domain_groups:
                if dg.domain_id == mir.domain_id:
                    mirrors_list.append(mir)

    for mir in mirrors_list:
        mirrors[mir.id] = mir.mirror_url

    return mirrors

def get_domain_subset(dg_id):
    """
    Get subset of domains based on user's domain group
    """
    initial_domain_list = Domain.query.all()
    domain_groups = DGDomain.query.filter_by(domain_group_id=dg_id).all()
    domain_subset = []
    for dom in initial_domain_list:
        for dg in domain_groups:
            if dg.domain_id == dom.id:
                domain_subset.append(dom)

    return domain_subset

def auth_user(user_dg_id, domain):
    """
    Does this user have access to this domain?
    """
    domain_groups = DGDomain.query.filter_by(domain_group_id=user_dg_id).all()
    domain = Domain.query.filter_by(domain=domain).first_or_404()
    auth = False
    for ddg in domain_groups:
        if ddg.domain_id == domain.id:
            auth = True

    return auth

def get_recent_domain_reports(domain_choice):
    """
    Get most recent domain reports for a domain
    """
    # Find Domain ID for choice
    now = datetime.datetime.now()
    domain = Domain.query.filter_by(domain=domain_choice).first()
    reports = Report.query.filter_by(domain_id=domain.id).all()
    recent_reports = []
    for rp in reports:
        numdays = (now - rp.date_reported).days
        if numdays > 7:
            continue
        mirror = Mirror.query.filter_by(id=rp.mirror_id).first()
        recent_report = {
            'domain_status': rp.domain_status,
            'mirror': mirror.mirror_url,
            'mirror_status': rp.mirror_status,
            'user_agent': rp.user_agent,
            'ip': rp.ip,
            'date_reported': rp.date_reported
        }
        recent_reports.append(recent_report)
    
    logger.debug(recent_reports)
    return recent_reports
        

def bad_domains(admin, dg_id):
    now = datetime.datetime.now()
    if admin:
        dg_id = False
    domains = get_domain_list(dg_id)
    bad_domains = []
    bad_domains_list = Report.query.filter(Report.domain_status != 200).distinct(Report.domain_id)
    for bd in bad_domains_list:
        numdays = (now - bd.date_reported).days
        if numdays > 7:
            continue
        if bd.domain_id not in domains:
            continue
        bad_dom = {
            'domain': domains[bd.domain_id],
            'status': bd.domain_status,
            'date_reported': bd.date_reported,
        }
        bad_domains.append(bad_dom)

    return bad_domains
    
def bad_mirrors(admin, dg_id):
    now = datetime.datetime.now()
    if admin:
        dg_id = False
    domains = get_domain_list(dg_id)
    mirrors = mirror_list(dg_id)
    bad_mirrors = {
        'onions': [],
        'cloudfront': [],
        'azure': [],
        'fastly': [],
        'other': []
    }
    bad_mirrors_list = Report.query.filter(Report.mirror_status != 200).all()
    for bm in bad_mirrors_list:
        numdays = (now - bm.date_reported).days
        if int(numdays) > 7:
            continue
        if bm.domain_id not in domains:
            continue
        bad_mir = {
            'domain': domains[bm.domain_id],
            'mirror': mirrors[bm.mirror_id],
            'status': bm.mirror_status,
            'date_reported': bm.date_reported,
        }
        if '.onion' in mirrors[bm.mirror_id]:
            bad_mirrors['onions'].append(bad_mir)
        elif 'fastly.net' in mirrors[bm.mirror_id]:
            bad_mirrors['fastly'].append(bad_mir)
        elif 'cloudfront.net' in mirrors[bm.mirror_id]:
            bad_mirrors['cloudfront'].append(bad_mir)
        elif 'azureedge.net' in mirrors[bm.mirror_id]:
            bad_mirrors['azure'].append(bad_mir)
        else:
            bad_mirrors['other'].append(bad_mir)

    print(bad_mirrors)
    return bad_mirrors

def monthly_bad(admin, dg_id):
    today = datetime.datetime.today()
    last_month = today - datetime.timedelta(days=30)
    if admin:
        dg_id = False
    domains = get_domain_list(dg_id)
    domain_bad_count = {}
    mirrors = mirror_list(dg_id)
    mirror_bad_count = {}
    reports_list = Report.query.filter(Report.date_reported > last_month).all()
    for report in reports_list:
        if report.domain_status != 200:
            if report.domain_id in domain_bad_count:
                domain_bad_count[report.domain_id] += 1
            else:
                domain_bad_count[report.domain_id] = 1
        if report.mirror_status != 200:
            if report.mirror_id in mirror_bad_count:
                mirror_bad_count[report.mirror_id] += 1
            else:
                mirror_bad_count[report.mirror_id] = 1

    final_report = []
    for db in domain_bad_count:
        fp = {
            'url': domains[db],
            'count': domain_bad_count[db]
        }
        final_report.append(fp)
    for mir in mirror_bad_count:
        mp = {
            'url': mirrors[mir],
            'count': mirror_bad_count[mir]
        }
        final_report.append(mp)

    sorted_final = sorted(final_report, key=lambda x: x['count'], reverse=True)

    return sorted_final
