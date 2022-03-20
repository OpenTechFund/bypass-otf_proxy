import os
import subprocess

from app import app


def terraform_init(provider):
    subprocess.run(
        ['terraform', 'init'],
        cwd=os.path.join(
            app.config['TERRAFORM_DIRECTORY'],
            provider))


def terraform_plan(provider):
    plan = subprocess.run(
        ['terraform', 'plan'],
        cwd=os.path.join(
            app.config['TERRAFORM_DIRECTORY'],
            provider))


def terraform_apply(provider: str, refresh: bool = True, parallelism: int = 10):
    subprocess.run(
        ['terraform', 'apply', f'-refresh={str(refresh).lower()}', '-auto-approve', f'-parallelism={str(parallelism)}'],
        cwd=os.path.join(
            app.config['TERRAFORM_DIRECTORY'],
            provider))
