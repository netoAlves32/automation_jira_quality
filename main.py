# This snippet has been automatically generated and should be regarded as a
# code template only.
# It will require modifications to work:
# - It may require correct/in-range values for request initialization.
# - It may require specifying regional endpoints when creating the service
#   client as shown in:
#   https://googleapis.dev/python/google-api-core/latest/client_options.html

from google.cloud import storage
from utils.utils import (get_config_from_gcs, 
                   parse_args, 
                   generate_data_scan
                   )

import logging
import sys

LOGGER: logging.Logger = logging.getLogger("process_data")

stg_client = storage.Client()

def run_job(config: dict) -> None:
    """
    Runs the pyspark job

    Arguments:
        config: The config necessary to run the job.
    """
    generate_data_scan(config,stg_client)
    print(f"Completed Task.")
    return


if __name__ == '__main__':
    LOGGER.setLevel(logging.INFO)

    LOGGER.warning("Parsing args from caller...")
    # print(sys.argv)
    args = parse_args()
    LOGGER.warning(f"Job's configuration:\n{args}")
    config = get_config_from_gcs(stg_client, args["configbucket"], args["configblob"])
    config.update({
            "projectid": args["projectid"],
            "configbucket": args["configbucket"],
            "configblob": args["configblob"],
            "labels" : {
                "application" : args["labelapplication"],
                "costcenter" : args["labelcostcenter"],
                "environment" : args.get("labelenvironment",args["projectid"])
            }
    })
    LOGGER.warning(f"Job's configuration:\n{config}")
    run_job(config)
