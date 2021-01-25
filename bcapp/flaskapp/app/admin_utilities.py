import datetime
import logging
from app import app
from app.models import User, Token, Domain, Mirror, Report, LogReport
from . import db

logger = logging.getLogger('logger')

def log_report_list():
    """
    Generate list of log reports
    """
    domains = domain_list()
    log_reports_list = LogReport.query.all()
    log_reports = []
    for rpt in log_reports_list:
        log_report = {
            'id':rpt.id,
            'domain':domains[rpt.domain_id],
            'date':rpt.date_of_report,
            'report_text':rpt.report,
            'first_date':rpt.first_date_of_log,
            'last_date':rpt.last_date_of_log,
            'hits':rpt.hits
        }
        log_reports.append(log_report)
    logger.debug(log_reports)
    return log_reports

def domain_list():
    """
    Generate list of domains
    """
    domains = {}
    domains_list = Domain.query.all()
    for dom in domains_list:
        domains[dom.id] = dom.domain
    return domains

def mirror_list():
    """
    Generate list of mirrors
    """
    mirrors = {}
    mirrors_list = Mirror.query.all()
    for mir in mirrors_list:
        mirrors[mir.id] = mir.mirror_url

    return mirrors

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
        

def bad_domains():
    now = datetime.datetime.now()
    domains = domain_list()
    bad_domains = []
    bad_domains_list = Report.query.filter(Report.domain_status != 200).distinct(Report.domain_id)
    for bd in bad_domains_list:
        numdays = (now - bd.date_reported).days
        if numdays > 7:
            continue
        bad_dom = {
            'domain': domains[bd.domain_id],
            'status': bd.domain_status,
            'date_reported': bd.date_reported,
        }
        bad_domains.append(bad_dom)

    return bad_domains
    
def bad_mirrors():
    now = datetime.datetime.now()
    domains = domain_list()
    mirrors = mirror_list()
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

def monthly_bad():
    today = datetime.datetime.today()
    last_month = today - datetime.timedelta(days=30)
    domains = domain_list()
    domain_bad_count = {}
    mirrors = mirror_list()
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
