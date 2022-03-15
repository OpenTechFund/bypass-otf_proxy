import json
import os

import jinja2

from app import app, mirror_sites
from app.extensions import db
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

data "gitlab_project" "this" {
  id = "{{ gitlab_project }}"
}

resource "gitlab_repository_file" "this" {
  project        = data.gitlab_project.this.id
  file_path      = "{{ gitlab_file_v2 }}"
  branch         = "main"
  content        = base64encode(file("{{ gitlab_file_v2 }}"))
  author_email   = "{{ gitlab_author_email }}"
  author_name    = "{{ gitlab_author_name }}"
  commit_message = "{{ gitlab_commit_message }}"
}
"""


def generate_terraform():
    tmpl = jinja2.Template(TEMPLATE)
    rendered = tmpl.render(
        gitlab_token=app.config['GITLAB_TOKEN'],
        gitlab_project=app.config['GITLAB_PROJECT'],
        gitlab_file_v2=app.config['GITLAB_FILE_V2'],
        gitlab_author_email=app.config['GITLAB_AUTHOR_EMAIL'],
        gitlab_author_name=app.config['GITLAB_AUTHOR_NAME'],
        gitlab_commit_message=app.config['GITLAB_COMMIT_MESSAGE']
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
            app.config['GITLAB_FILE_V2']
    ), 'w') as out:
        json.dump(mirror_sites(), out, indent=4, sort_keys=True)


if __name__ == "__main__":
    db.init_app(app)
    with app.app_context():
        generate_terraform()
        terraform_init("gitlab")
        terraform_apply("gitlab")
