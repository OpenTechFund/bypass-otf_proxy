Python App to set up and maintain mirrors.

# Setup 

```
cd proxy_automation
export PIPENV_VENV_IN_PROJECT=1 (optional)
pipenv install
pipenv shell
```

# Usage

## CDN/Github setup

```
python automation.py
```

There are two modes - adding a domain proxy/mirror, or testing (Domain addition is the default.) 

### Domain addition: 
The automation script will ask you for the domain, whether to add it to Cloudfront, Fastly and Azure (default is 'no' for each.)

If you want a cloudfront distro, it will create that for you, and tell you the domain. For Fastly and Azure, you'll have to specify the Fastly and Azure subdomain (Cloudfront specifies a subdomain for you, Fastly and Azure require you to define it.)

There are some defaults for all three CDN systems, and if you want to change those, you would need to go to the documentation for each and modify the code:

* [Cloudfront](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudfront.html#CloudFront.Client.create_distribution)
* [Fastly](https://docs.fastly.com/api/config) and [Fastly-Python](https://github.com/maxpearl/fastly-py)
* [Azure](https://docs.microsoft.com/en-us/python/api/overview/azure/cdn?view=azure-python)

If you want to add to a Github repository, it will update them accordingly if you've created new mirrors - otherwise it will ask you for mirrors to add or replace.

All configurations are in auto.cfg (see auto.cfg-example) You need:

- an AWS account that has permission to create Cloudfront Distributions
- a Fastly account that has permission to create new configurations
- an Azure account with permissions to create new CDN distributions
- a Github repo for mirrors in JSON format that is read by the [Bypass Censorship Extension](https://github.com/OpenTechFund/bypass-censorship-extension) browser extension. An example [is here](https://github.com/OpenTechFund/bypass-mirrors)

### Testing:

The script will cycle through each domain in the mirror json file, and test for response codes. It will determine the number of domains with errors, and return which ones have errors. It will also return any domains without a usable mirror.