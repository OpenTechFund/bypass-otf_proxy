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
    github = {
      source = "integrations/github"
      version = "~> 4.20.1"
    }
  }
}

{% for list in lists %}
provider "github" {
  alias               = "list_{{ list.id }}"
  owner               = "{{ list.container.split("/")[0] }}"
  token               = "{{ github_api_key }}"
}

data "github_repository" "repository_{{ list.id }}" {
  provider            = github.list_{{ list.id }}
  name                = "{{ list.container.split("/")[1] }}"
}

resource "github_repository_file" "file_{{ list.id }}" {
  provider            = github.list_{{ list.id }}
  repository          = data.github_repository.repository_{{ list.id }}.name
  branch              = "master"
  file                = "{{ list.filename }}"
  content             = file("v2.json")
  commit_message      = "Managed by Terraform"
  commit_author       = "Terraform User"
  commit_email        = "terraform@api.otf.is"
  overwrite_on_create = true
}
{% endfor %}
"""


def generate_terraform():
    lists = MirrorList.query.filter(
        MirrorList.destroyed == None,
        MirrorList.provider == "github"
    ).all()
    tmpl = jinja2.Template(TEMPLATE)
    rendered = tmpl.render(
        github_api_key=app.config['GITHUB_API_KEY'],
        lists = lists
    )
    with open(os.path.join(
            app.config['TERRAFORM_DIRECTORY'],
            'github',
            'main.tf'
    ), 'w') as out:
        out.write(rendered)
    with open(os.path.join(
            app.config['TERRAFORM_DIRECTORY'],
            'github',
            'v2.json'
    ), 'w') as out:
        json.dump(mirror_sites(), out, indent=2, sort_keys=True)


if __name__ == "__main__":
    db.init_app(app)
    with app.app_context():
        generate_terraform()
        terraform_init("github")
        terraform_apply("github")
