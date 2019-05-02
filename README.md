Python App to set up and maintain mirrors.

# Setup 

```
export PIPENV_VENV_IN_PROJECT=1
pipenv install
pipenv shell
```

# Usage

## CDN/Github setup

```
cd proxy_automation
python automation.py
```

The automation script will ask you for the domain, whether to add it to Cloudfront, the mirror Github repo, or both.
If you want a cloudfront distro, it will create that for you, and tell you the domain.
If you want to add to a Github repository, it will then ask for the mirror domains, and update them accordingly.

All configurations for AWS and GitHub are in auto.cfg (see auto.cfg-example) You need:

- an AWS account that has permission to create Cloudfront Distributions
- a Github repo for mirrors that is read by the [Bypass Censorship Extension](https://github.com/OpenTechFund/bypass-censorship-extension) browser extension. 