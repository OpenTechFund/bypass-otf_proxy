from app.extensions import db
from app.models import Alarm


def _get_alarm(target: str,
               alarm_type: str,
               proxy_id=None,
               create_if_missing=True):
    if target == "proxy":
        alarm = Alarm.query.filter(
            Alarm.target == "proxy",
            Alarm.alarm_type == alarm_type,
            Alarm.proxy_id == proxy_id
        ).first()
    if create_if_missing and alarm is None:
        alarm = Alarm()
        alarm.target = target
        alarm.alarm_type = alarm_type
        if target == "proxy":
            alarm.proxy_id = proxy_id
        db.session.add(alarm)
        db.session.commit()
    return alarm


def get_proxy_alarm(proxy_id: int, alarm_type: str):
    return _get_alarm("proxy", "alarm_type", proxy_id=proxy_id)
