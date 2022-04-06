from app import app
from app.terraform.list import ListAutomation


class ListGitlabAutomation(ListAutomation):
    short_name = "list_gitlab"
    provider = "gitlab"

    template_parameters = [
        "gitlab_token",
        "gitlab_author_email",
        "gitlab_author_name",
        "gitlab_commit_message"
    ]

    template = """
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


if __name__ == "__main__":
    with app.app_context():
        auto = ListGitlabAutomation
        auto.generate_terraform()
        auto.terraform_init()
        auto.terraform_apply()
