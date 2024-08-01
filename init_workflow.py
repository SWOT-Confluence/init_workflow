"""Initialize Confluence workflow

Initializes Confluence workflow by:
1) Ensuring teh EFS directories are set up
2) Downloading required data for SWORD, gauges, and reaches of interest subset file (reaches of interest, gauge data, and sword)

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
SWORD_PATCHES = EFS_DIR_INPUT.joinpath("sword_patches_v216.json")


logging.getLogger().setLevel(logging.INFO)
logging.basicConfig(format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%dT%H:%M:%S',
                    level=logging.INFO)


def init_workflow():
    """Initialize the confluence workflow."""
    
    arg_parser = create_args()
    args = arg_parser.parse_args()
    prefix = args.prefix
    reaches_of_interest = args.reachsubset
    logging.info("Prefix: %s", prefix)
    if reaches_of_interest:
        logging.info("Reachs of interest: %s", reaches_of_interest)
    
    # Set up EFS directories
    set_up_efs()
    logging.info("Set up the EFS directories.")
    
    # Download required data
    download_data(prefix, reaches_of_interest)
    logging.info("Downloaded required input data.")


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
    return arg_parser


def set_up_efs():
    """Set up EFS directories."""
    
    EFS_DIR_INPUT.joinpath("gage").mkdir(parents=True, exist_ok=True)
    EFS_DIR_INPUT.joinpath("sos").mkdir(parents=True, exist_ok=True)
    EFS_DIR_INPUT.joinpath("sword").mkdir(parents=True, exist_ok=True)
    EFS_DIR_INPUT.joinpath("swot").mkdir(parents=True, exist_ok=True)
    
    EFS_DIR_FLPE.joinpath("geobam").mkdir(parents=True, exist_ok=True)
    EFS_DIR_FLPE.joinpath("hivdi").mkdir(parents=True, exist_ok=True)
    EFS_DIR_FLPE.joinpath("metroman").mkdir(parents=True, exist_ok=True)
    EFS_DIR_FLPE.joinpath("momma").mkdir(parents=True, exist_ok=True)
    EFS_DIR_FLPE.joinpath("sad").mkdir(parents=True, exist_ok=True)
    EFS_DIR_FLPE.joinpath("sic4dvar").mkdir(parents=True, exist_ok=True)
    
    EFS_DIR_DIAGNOSTICS.joinpath("prediagnostics").mkdir(parents=True, exist_ok=True)
    EFS_DIR_DIAGNOSTICS.joinpath("postdiagnostics").joinpath("basin").mkdir(parents=True, exist_ok=True)
    EFS_DIR_DIAGNOSTICS.joinpath("postdiagnostics").joinpath("reach").mkdir(parents=True, exist_ok=True)
    
    EFS_DIR_VALIDATION.joinpath("figs").mkdir(parents=True, exist_ok=True)
    
    EFS_DIR_OUTPUT.joinpath("sos").mkdir(parents=True, exist_ok=True)
    
    EFS_DIR_LOGS.joinpath("sic4dvar").mkdir(parents=True, exist_ok=True)


def download_data(prefix, reaches_of_interest):
    """Download data needed to run the Confluence workflow."""
    
    s3 = boto3.client("s3")
    
    config_bucket = f"{prefix}-config"
    if reaches_of_interest:
        s3.download_file(
            config_bucket, 
            reaches_of_interest, 
            EFS_DIR_INPUT.joinpath(reaches_of_interest)
        )
        logging.info("Downloaded %s/%s to %s", config_bucket, reaches_of_interest, EFS_DIR_INPUT.joinpath(reaches_of_interest))
    
    if not SWORD_PATCHES.exists():  
        s3.download_file(
                config_bucket, 
                sword_patches.name, 
                SWORD_PATCHES
            )
        logging.info("Downloaded %s/%s to %s", config_bucket, SWORD_PATCHES.name, SWORD_PATCHES)
    
    download_directory(s3, config_bucket, "gage")
    download_directory(s3, config_bucket, "sword")
    
    json_bucket = f"{prefix}-json"
    s3.download_file(
        json_bucket, 
        "continent-setfinder.json", 
        EFS_DIR_INPUT.joinpath("continent-setfinder.json")
    )
    logging.info("Downloaded %s/continent-setfinder.json to %s", json_bucket, EFS_DIR_INPUT.joinpath("continent-setfinder.json"))


def download_directory(s3, config_bucket, prefix):
    """Download all files located at prefix."""
    
    paginator = s3.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(
        Bucket=config_bucket,
        Prefix=prefix
    )
    items = [key["Key"] for page in page_iterator for key in page["Contents"]]
    for item in items:
        efs_file = EFS_DIR_INPUT.joinpath(item)
        if not efs_file.exists():
            s3.download_file(
                config_bucket, 
                item,
                efs_file
            )
            logging.info("Downloaded %s/%s to %s", config_bucket, item, efs_file)
        else:
            logging.info("Not downloading %s", efs_file)


if __name__ == "__main__":
    init_workflow()