#!/usr/bin/env python

# import ipdb; ipdb.set_trace()

from common.utils_openapi import substitute_at_position, redefine_paths, redefine_definitions, add_custom_gcp_entries

import yaml
from app.main import app

if __name__ == "__main__":

    openapi = app.swagger2()

    # Redefine paths
    openapi = redefine_paths(openapi)

    # Substitute definitions
    openapi = redefine_definitions(openapi)

    # Add custom gcp entries
    openapi = add_custom_gcp_entries(openapi)

    with open("openapi.yaml", "w") as f:
        yaml.safe_dump(openapi, f, sort_keys=False)