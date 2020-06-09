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
    print(log_reports)
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

def bad_domains():
    now = datetime.datetime.now()
    domains = domain_list()
    bad_domains = []
    bad_domains_list = Report.query.filter(Report.domain_status != 200)
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
    bad_mirrors = []
    bad_mirrors_list = Report.query.filter(Report.mirror_status != '200').all()
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
        bad_mirrors.append(bad_mir)

    return bad_mirrors

def bad_onions():
    return



