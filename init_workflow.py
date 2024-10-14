"""Initialize Confluence workflow

Initializes Confluence workflow by:
1) Ensuring the EFS directories are set up
2) Downloading required data for SWORD, gauges, and reaches of interest subset file (reaches of interest, gauge data, and sword)
3) Uploading continent-setfinder.json file to JSON S3 bucket

* Note only downloads gauge and sword data if it does not exist.
"""

# Standard imports
import argparse
import logging
import pathlib

# Third-party imports
import boto3
import botocore

# Constants
EFS_DIR_INPUT = pathlib.Path("/mnt/input")
EFS_DIR_FLPE = pathlib.Path("/mnt/flpe")
EFS_DIR_MOI = pathlib.Path("/mnt/moi")
EFS_DIR_DIAGNOSTICS = pathlib.Path("/mnt/diagnostics")
EFS_DIR_OFFLINE = pathlib.Path("/mnt/offline")
EFS_DIR_VALIDATION = pathlib.Path("/mnt/validation")
EFS_DIR_OUTPUT = pathlib.Path("/mnt/output")
EFS_DIR_LOGS = pathlib.Path("/mnt/logs")
S3 = boto3.client("s3")
SWORD_PATCHES = EFS_DIR_INPUT.joinpath("sword_patches_v216.json")


logging.getLogger().setLevel(logging.INFO)
logging.basicConfig(format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%dT%H:%M:%S',
                    level=logging.INFO)


def init_workflow():
    """Initialize the confluence workflow."""
    
    arg_parser = create_args()
    args = arg_parser.parse_args()
    delete_map_state = args.deletemap
    prefix = args.prefix
    reaches_of_interest = args.reachsubset
    logging.info("Delete map state from S3: %s", delete_map_state)
    logging.info("Prefix: %s", prefix)
    if reaches_of_interest:
        logging.info("Reachs of interest: %s", reaches_of_interest)
    
    # Set up EFS directories
    set_up_efs()
    logging.info("Set up the EFS directories.")
    
    # Download required data
    download_data(prefix, reaches_of_interest)
    logging.info("Downloaded required input data.")

    # Remove map state data
    if delete_map_state:
        s3_map = f"{prefix}-map-state"
        delete_s3_map_state(s3_map)


def create_args():
    """Create and return argparser with arguments."""

    arg_parser = argparse.ArgumentParser(description="Initialize confluence workflow")
    arg_parser.add_argument("-p",
                            "--prefix",
                            type=str,
                            help="Prefix for AWS environment.")
    arg_parser.add_argument("-r",
                            "--reachsubset",
                            type=str,
                            default="",
                            help="Name of reaches of interest file to subset reaches.")
    arg_parser.add_argument("-d",
                            "--deletemap",
                            action="store_true",
                            help="Indicator to delete S3 map state bucket.")
    return arg_parser


def set_up_efs():
    """Set up EFS directories."""

    EFS_DIR_INPUT.joinpath("gage").mkdir(parents=True, exist_ok=True)
    EFS_DIR_INPUT.joinpath("gage").joinpath("Rtarget").mkdir(parents=True, exist_ok=True)
    EFS_DIR_INPUT.joinpath("sos").mkdir(parents=True, exist_ok=True)
    EFS_DIR_INPUT.joinpath("sword").mkdir(parents=True, exist_ok=True)
    EFS_DIR_INPUT.joinpath("swot").mkdir(parents=True, exist_ok=True)

    EFS_DIR_FLPE.joinpath("geobam").mkdir(parents=True, exist_ok=True)
    EFS_DIR_FLPE.joinpath("hivdi").mkdir(parents=True, exist_ok=True)
    EFS_DIR_FLPE.joinpath("metroman").mkdir(parents=True, exist_ok=True)
    EFS_DIR_FLPE.joinpath("metroman").joinpath("sets").mkdir(parents=True, exist_ok=True)
    EFS_DIR_FLPE.joinpath("momma").mkdir(parents=True, exist_ok=True)
    EFS_DIR_FLPE.joinpath("sad").mkdir(parents=True, exist_ok=True)
    EFS_DIR_FLPE.joinpath("sic4dvar").mkdir(parents=True, exist_ok=True)

    EFS_DIR_DIAGNOSTICS.joinpath("prediagnostics").mkdir(parents=True, exist_ok=True)
    EFS_DIR_DIAGNOSTICS.joinpath("postdiagnostics").joinpath("basin").mkdir(parents=True, exist_ok=True)
    EFS_DIR_DIAGNOSTICS.joinpath("postdiagnostics").joinpath("reach").mkdir(parents=True, exist_ok=True)

    EFS_DIR_VALIDATION.joinpath("figs").mkdir(parents=True, exist_ok=True)
    EFS_DIR_VALIDATION.joinpath("stats").mkdir(parents=True, exist_ok=True)

    EFS_DIR_OUTPUT.joinpath("sos").mkdir(parents=True, exist_ok=True)

    EFS_DIR_LOGS.joinpath("sic4dvar").mkdir(parents=True, exist_ok=True)


def download_data(prefix, reaches_of_interest):
    """Download data needed to run the Confluence workflow."""

    config_bucket = f"{prefix}-config"
    if reaches_of_interest:
        S3.download_file(
            config_bucket, 
            reaches_of_interest, 
            EFS_DIR_INPUT.joinpath(reaches_of_interest)
        )
        logging.info("Downloaded %s/%s to %s", config_bucket, reaches_of_interest, EFS_DIR_INPUT.joinpath(reaches_of_interest))

    cont_setfinder = EFS_DIR_INPUT.joinpath("continent-setfinder.json")
    S3.download_file(
        config_bucket, 
        "continent-setfinder.json", 
        cont_setfinder
    )
    logging.info("Downloaded %s/continent-setfinder.json to %s", config_bucket, cont_setfinder)

    json_bucket = f"{prefix}-json"
    S3.upload_file(
        cont_setfinder,
        json_bucket, 
        "continent-setfinder.json",
        ExtraArgs={
            "ServerSideEncryption": "aws:kms"
        }
    )
    logging.info("Uploaded %s to %s/continent-setfinder.json", cont_setfinder, json_bucket)

    if not SWORD_PATCHES.exists():  
        S3.download_file(
                config_bucket, 
                SWORD_PATCHES.name, 
                SWORD_PATCHES
            )
        logging.info("Downloaded %s/%s to %s", config_bucket, SWORD_PATCHES.name, SWORD_PATCHES)

    download_directory(config_bucket, "gage")
    download_directory(config_bucket, "sword")


def download_directory(config_bucket, prefix):
    """Download all files located at prefix."""

    paginator = S3.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(
        Bucket=config_bucket,
        Prefix=prefix
    )
    items = [key["Key"] for page in page_iterator for key in page["Contents"]]
    for item in items:
        efs_file = EFS_DIR_INPUT.joinpath(item)
        if not efs_file.exists():
            S3.download_file(
                config_bucket, 
                item,
                efs_file
            )
            logging.info("Downloaded %s/%s to %s", config_bucket, item, efs_file)
        else:
            logging.info("Not downloading %s", efs_file)


def delete_s3_map_state(s3_map):
    """Delete S3 Map State bucket contents."""

    paginator = S3.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(
        Bucket=s3_map
    )
    key_count = list(page_iterator)[0]["KeyCount"]
    if key_count > 0:
        items = { "Objects": [ {"Key": key["Key"] } for page in page_iterator for key in page["Contents"]]}
        S3.delete_objects(Bucket=s3_map, Delete=items)
        for item in items["Objects"]: logging.info("Deleted s3://%s/%s", s3_map, item["Key"])


if __name__ == "__main__":
    init_workflow()