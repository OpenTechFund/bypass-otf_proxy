import json
import os

import jinja2

from app import app, mirror_sites
from app.extensions import db
from app.models import MirrorList
from app.terraform import terraform_init, terraform_apply

TEMPLATE = """
terraform {
  required_providers {
    gitlab = {
      source = "gitlabhq/gitlab"
      version = "~> 3.12.0"
    }
  }
}

provider "gitlab" {
  token = "{{ gitlab_token }}"
}

{% for list in lists %}
data "gitlab_project" "project_{{ list.id }}" {
  id = "{{ list.container }}"
}

resource "gitlab_repository_file" "file_{{ list.id }}" {
  project        = data.gitlab_project.project_{{ list.id }}.id
  file_path      = "{{ list.filename }}"
  branch         = "{{ list.branch }}"
  content        = base64encode(file("{{ list.format }}.json"))
  author_email   = "{{ gitlab_author_email }}"
  author_name    = "{{ gitlab_author_name }}"
  commit_message = "{{ gitlab_commit_message }}"
}

{% endfor %}
"""


def generate_terraform():
    lists = MirrorList.query.filter(
        MirrorList.destroyed == None,
        MirrorList.provider == "gitlab"
    ).all()
    tmpl = jinja2.Template(TEMPLATE)
    rendered = tmpl.render(
        gitlab_token=app.config['GITLAB_TOKEN'],
        gitlab_author_email=app.config['GITLAB_AUTHOR_EMAIL'],
        gitlab_author_name=app.config['GITLAB_AUTHOR_NAME'],
        gitlab_commit_message=app.config['GITLAB_COMMIT_MESSAGE'],
        lists=lists
    )
    with open(os.path.join(
            app.config['TERRAFORM_DIRECTORY'],
            'gitlab',
            'main.tf'
    ), 'w') as out:
        out.write(rendered)
    with open(os.path.join(
            app.config['TERRAFORM_DIRECTORY'],
            'gitlab',
            'v2.json'
    ), 'w') as out:
        json.dump(mirror_sites(), out, indent=4, sort_keys=True)


if __name__ == "__main__":
    db.init_app(app)
    with app.app_context():
        generate_terraform()
        terraform_init("gitlab")
        terraform_apply("gitlab")
