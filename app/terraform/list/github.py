from app import app
from app.terraform.list import ListAutomation


class ListGithubAutomation(ListAutomation):
    short_name = "list_github"
    provider = "github"

    template_parameters = [
        "github_api_key"
    ]

    template = """
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
      branch              = "{{ list.branch }}"
      file                = "{{ list.filename }}"
      content             = file("{{ list.format }}.json")
      commit_message      = "Managed by Terraform"
      commit_author       = "Terraform User"
      commit_email        = "terraform@api.otf.is"
      overwrite_on_create = true
    }
    {% endfor %}
    """


if __name__ == "__main__":
    with app.app_context():
        auto = ListGithubAutomation()
        auto.generate_terraform()
        auto.terraform_init()
        auto.terraform_apply()
