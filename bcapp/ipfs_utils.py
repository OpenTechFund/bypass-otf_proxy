import sh

def ipfs_add(**kwargs):
    """
    Not yet automated
    :kwarg <domain>
    :returns ifps from user input
    """
    mirror = input(f"Hash of IPFS Node for {kwargs['domain']}?")
    return mirror

