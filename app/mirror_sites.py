from app.models import Origin


def mirror_sites():
    return {
        "version": "2.0",
        "sites": [{
            "main_domain": x.domain_name.replace("www.", ""),
            "available_alternatives": [
                                          {
                                              "proto": "tor" if ".onion" in a.url else "https",
                                              "type": "eotk" if ".onion" in a.url else "mirror",
                                              "created_at": str(a.added),
                                              "updated_at": str(a.updated),
                                              "url": a.url
                                          } for a in x.mirrors if not a.deprecated and not a.destroyed
                                      ] + [
                                          {
                                              "proto": "https",
                                              "type": "mirror",
                                              "created_at": str(a.added),
                                              "updated_at": str(a.updated),
                                              "url": a.url
                                          } for a in x.proxies if
                                          a.url is not None and not a.deprecated and not a.destroyed and a.provider == "cloudfront"
                                      ]} for x in Origin.query.order_by(Origin.domain_name).all()
        ]
    }
