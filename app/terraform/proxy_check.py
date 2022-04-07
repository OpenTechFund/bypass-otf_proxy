import requests

from app import app
from app.extensions import db
from app.models import AlarmState, Alarm, Proxy


def set_http_alarm(proxy_id: int, state: AlarmState, text: str):
    alarm = Alarm.query.filter(
        Alarm.proxy_id == proxy_id,
        Alarm.alarm_type == "http-status"
    ).first()
    if alarm is None:
        alarm = Alarm()
        alarm.proxy_id = proxy_id
        alarm.alarm_type = "http-status"
        db.session.add(alarm)
    alarm.update_state(state, text)


def check_http():
    proxies = Proxy.query.filter(
        Proxy.destroyed == None
    )
    for proxy in proxies:
        try:
            if proxy.url is None:
                continue
            r = requests.get(proxy.url,
                             allow_redirects=False,
                             timeout=5)
            r.raise_for_status()
            if r.is_redirect:
                set_http_alarm(
                    proxy.id,
                    AlarmState.CRITICAL,
                    f"{r.status_code} {r.reason}"
                )
            else:
                set_http_alarm(
                    proxy.id,
                    AlarmState.OK,
                    f"{r.status_code} {r.reason}"
                )
        except (requests.ConnectionError, requests.Timeout):
            set_http_alarm(
                proxy.id,
                AlarmState.CRITICAL,
                f"Connection failure")
        except requests.HTTPError:
            set_http_alarm(
                proxy.id,
                AlarmState.CRITICAL,
                f"{r.status_code} {r.reason}"
            )


if __name__ == "__main__":
    with app.app_context():
        check_http()
