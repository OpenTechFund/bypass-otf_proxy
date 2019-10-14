Python App to set up and maintain mirrors.

# Setup 

```
cd bcapp
export PIPENV_VENV_IN_PROJECT=1 (optional)
pipenv install
pipenv shell
```

# Usage
```
Usage: automation.py [OPTIONS]

Options:
  --testing [onions|noonions|domains]
                                  Domain testing of available mirrors - choose
                                  onions, nonions, or domains
  --domain TEXT                   Domain to add/change to mirror list
  --existing TEXT                 Mirror exists already, just add to github.
  --replace TEXT                  Mirror/onion to replace.
  --delete_domain                 Delete a domain from list
  --domain_list                   List all domains and mirrors/onions
  --mirror_detail TEXT              List mirrors for domain
  --mirror_type [cloudfront|azure|ecs|fastly|onion]
                                  Type of mirror
  --nogithub                      Do not add to github
  --help                          Show this message and exit.
```

## Listing:

To get a list of all domains and mirrors use:
`python automation.py --domain_list`

To get a list of one domain and it's mirrors (and test each) use:
`python automation.py --mirror_detail --domain=domain.com`
or just
`python automation.py --domain=domain.com`

## Testing:

`python automation.py --testing=domains|onions|noonions`

The 'domains' option just tests the actual domains from whereever you are sitting. So if you are behind a potential block, you'll be able to see whether or not you can reach those domains.

The 'noonions' option will cycle through each domain in the mirror json file, and test for response codes for the standard http/https mirrors. It will determine the number of domains with errors, and return which ones have errors. It will also return any domains without a usable mirror.

The 'onions' option will do the same with onions. Tor has to be installed properly to test these.

## Domain addition: 

To add an existing mirror (one that you have already set up, including onions) use:

`python automation.py --domain=domain.com --existing=domain_mirror.com`

This will add a mirror (or onion, if it is a .onion) to the json file. If the domain doesn't exist in the json file, it will add the domain.

To add a new mirror, for Cloudfront, Fastly, Azure or ECS use:

`python automation.py --domain=domain.com --mirror_type=cloudfront|fastly|azure|ecs|onion`

(The cloudfront, fastly, azure and ecs processes are automated. The onion process is not.)

If you want a cloudfront distro, it will create that for you, and tell you the domain. For Fastly and Azure, you'll have to specify the Fastly and Azure subdomain (Cloudfront specifies a subdomain for you, Fastly and Azure require you to define it.)

All configurations are in auto.cfg (see auto.cfg-example) You need:

- an AWS account that has permission to create Cloudfront Distributions
- a Fastly account that has permission to create new configurations
- an Azure account with permissions to create new CDN distributions
- a Github repo for mirrors in JSON format that is read by the [Bypass Censorship Extension](https://github.com/OpenTechFund/bypass-censorship-extension) browser extension. An example [is here](https://github.com/OpenTechFund/bypass-mirrors)

If you want to add onions, the best method is using Alec Muffett's [EOTK (Enterprise Onion ToolKit)](https://github.com/alecmuffett/eotk). One way to mine vanity .onion addresses is to use [eschalot](https://github.com/ReclaimYourPrivacy/eschalot).

## Mirror replacement

To replace one mirror with another use:

`python automation.py --domain=domain.com --replace=oldmirror.com --existing=newmirror.com`

or
*(implemented for ecs and cloudfront so far)*

`python automation.py --domain=domain.com --replace=oldmirror.com --mirror_type=ecs|cloudfront|fastly|azure`

If the mirror_type is defined, the replacement will be automated, and whatever is needed to reset the mirror url will be done. 

## Domain Deletion

To delete an entire domain and it's mirrors/onions, use:

`python automation.py --domain=domain.com --delete`

## Notes

There are some defaults for all four systems, and if you want to change those, you would need to go to the documentation for each and modify the code:

* [Cloudfront](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudfront.html#CloudFront.Client.create_distribution)
* [Fastly](https://docs.fastly.com/api/config) and [Fastly-Python](https://github.com/maxpearl/fastly-py)
* [Azure](https://docs.microsoft.com/en-us/python/api/overview/azure/cdn?view=azure-python)