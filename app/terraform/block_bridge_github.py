import datetime
from time import timezone

from dateutil.parser import isoparse
from github import Github

from app import app
from app.models import Bridge


def check_blocks():
    g = Github(app.config['GITHUB_API_KEY'])
    repo = g.get_repo(app.config['GITHUB_BRIDGE_REPO'])
    for vp in app.config['GITHUB_BRIDGE_VANTAGE_POINTS']:
        results = repo.get_contents(f"recentResult_{vp}").decoded_content.decode('utf-8').splitlines()
        for result in results:
            parts = result.split("\t")
            if isoparse(parts[2]) < (datetime.datetime.now(timezone.utc) - datetime.timedelta(days=3)):
                continue
            if int(parts[1]) < 40:
                bridge = Bridge.query.filter(
                    Bridge.nickname == parts[0]
                ).first()
                bridge.deprecate()


if __name__ == "__main__":
    with app.app_context():
        check_blocks()
