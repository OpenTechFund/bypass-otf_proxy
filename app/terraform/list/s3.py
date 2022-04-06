from app import app
from app.terraform.list import ListAutomation


class ListGithubAutomation(ListAutomation):
    short_name = "list_s3"
    provider = "s3"

    template_parameters = [
        "aws_access_key",
        "aws_secret_key"
    ]

    template = """
    terraform {
      required_providers {
        aws = {
          version = "~> 4.4.0"
        }
      }
    }

    provider "aws" {
      access_key = "{{ aws_access_key }}"
      secret_key = "{{ aws_secret_key }}"
      region = "us-east-1"
    }

    {% for list in lists %}
    resource "aws_s3_bucket_object" "object_{{ list.id }}" {
      bucket              = data.github_repository.repository_{{ list.id }}.name
      file                = "{{ list.filename }}"
      source              = "{{ list.format }}.json"
      content_type        = "application/json"
      etag                = filemd5("{{ list.format }}.json")
    }
    {% endfor %}
    """


if __name__ == "__main__":
    with app.app_context():
        auto = ListGithubAutomation()
        auto.generate_terraform()
        auto.terraform_init()
        auto.terraform_apply()
