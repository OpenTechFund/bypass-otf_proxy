import json
import os

import jinja2

from app import app, mirror_sites
from app.extensions import db
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

provider "github" {
  owner = "{{ github_organization }}"
  token = "{{ github_api_key }}"
}

data "github_repository" "this" {
  name = "{{ github_repository }}"
}

resource "github_repository_file" "this" {
  repository          = data.github_repository.this.name
  branch              = "master"
  file                = "{{ github_file_v2 }}"
  content             = file("{{ github_file_v2 }}")
  commit_message      = "Managed by Terraform"
  commit_author       = "Terraform User"
  commit_email        = "terraform@api.otf.is"
  overwrite_on_create = true
}
"""


def generate_terraform():
    tmpl = jinja2.Template(TEMPLATE)
    rendered = tmpl.render(
        github_api_key=app.config['GITHUB_API_KEY'],
        github_organization=app.config['GITHUB_ORGANIZATION'],
        github_repository=app.config['GITHUB_REPOSITORY'],
        github_file_v2=app.config['GITHUB_FILE_V2']
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
            app.config['GITHUB_FILE_V2']
    ), 'w') as out:
        json.dump(mirror_sites(), out, indent=4, sort_keys=True)


if __name__ == "__main__":
    db.init_app(app)
    with app.app_context():
        generate_terraform()
        terraform_init("github")
        terraform_apply("github")
