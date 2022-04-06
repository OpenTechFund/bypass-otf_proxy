import json

from app import app
from app.mirror_sites import bridgelines, mirror_sites, mirror_mapping
from app.models import MirrorList
from app.terraform import BaseAutomation


class ListAutomation(BaseAutomation):
    def generate_terraform(self):
        self.write_terraform_config(
            self.template,
            lists=MirrorList.query.filter(
                MirrorList.destroyed == None,
                MirrorList.provider == self.provider,
            ).all(),
            global_namespace=app.config['GLOBAL_NAMESPACE'],
            **{
                k: app.config[k.upper()]
                for k in self.template_parameters
            }
        )
        with open(self.working_directory('bc2.json'), 'w') as out:
            json.dump(mirror_sites(), out, indent=2, sort_keys=True)
        with open(self.working_directory('bca.json'), 'w') as out:
            json.dump(mirror_mapping(), out, indent=2, sort_keys=True)
        with open(self.working_directory('bridgelines.json'), 'w') as out:
            json.dump(bridgelines(), out, indent=2, sort_keys=True)
