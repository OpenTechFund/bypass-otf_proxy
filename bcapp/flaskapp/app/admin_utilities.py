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