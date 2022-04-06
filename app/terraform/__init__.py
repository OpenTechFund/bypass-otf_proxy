import json
import os
import subprocess
from typing import Dict, Any

import jinja2

from app import app


class BaseAutomation:
    short_name = None

    def working_directory(self, filename=None):
        return os.path.join(
            app.config['TERRAFORM_DIRECTORY'],
            self.short_name or self.__class__.__name__.lower(),
            filename or ""
        )

    def write_terraform_config(self, template: str, **kwargs):
        tmpl = jinja2.Template(template)
        with open(self.working_directory("main.tf"), 'w') as tf:
            tf.write(tmpl.render(**kwargs))

    def terraform_init(self):
        subprocess.run(
            ['terraform', 'init'],
            cwd=self.working_directory())

    def terraform_plan(self):
        plan = subprocess.run(
            ['terraform', 'plan'],
            cwd=self.working_directory())

    def terraform_apply(self, refresh: bool = True, parallelism: int = 10):
        subprocess.run(
            ['terraform', 'apply', f'-refresh={str(refresh).lower()}', '-auto-approve',
             f'-parallelism={str(parallelism)}'],
            cwd=self.working_directory())

    def terraform_show(self) -> Dict[str, Any]:
        terraform = subprocess.run(
            ['terraform', 'show', '-json'],
            cwd=os.path.join(
                self.working_directory()),
            stdout=subprocess.PIPE)
        return json.loads(terraform.stdout)

    def terraform_output(self) -> Dict[str, Any]:
        terraform = subprocess.run(
            ['terraform', 'output', '-json'],
            cwd=os.path.join(
                self.working_directory()),
            stdout=subprocess.PIPE)
        return json.loads(terraform.stdout)
