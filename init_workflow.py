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
    EFS_DIR_INPUT.joinpath("gage").joinpath("Rtarget").mkdir(parents=True, exist_ok=True)
    EFS_DIR_INPUT.joinpath("ssc", "model_static_files").mkdir(parents=True, exist_ok=True)
    EFS_DIR_INPUT.joinpath("lakeflow", "ancillary").mkdir(parents=True, exist_ok=True)
    EFS_DIR_INPUT.joinpath("sos").mkdir(parents=True, exist_ok=True)
    EFS_DIR_INPUT.joinpath("sword").mkdir(parents=True, exist_ok=True)
    EFS_DIR_INPUT.joinpath("swot").mkdir(parents=True, exist_ok=True)
    EFS_DIR_INPUT.joinpath("ssc/model_static_files/nd_20250430/gl_20250522_2_m1").mkdir(parents=True, exist_ok=True)
    EFS_DIR_INPUT.joinpath("ssc/model_static_files/nd_20250430/gl_20250522_2_m2").mkdir(parents=True, exist_ok=True)

    EFS_DIR_FLPE.joinpath("geobam").mkdir(parents=True, exist_ok=True)
    EFS_DIR_FLPE.joinpath("hivdi").mkdir(parents=True, exist_ok=True)
    EFS_DIR_FLPE.joinpath("metroman").mkdir(parents=True, exist_ok=True)
    EFS_DIR_FLPE.joinpath("metroman").joinpath("sets").mkdir(parents=True, exist_ok=True)
    EFS_DIR_FLPE.joinpath("momma").mkdir(parents=True, exist_ok=True)
    EFS_DIR_FLPE.joinpath("sad").mkdir(parents=True, exist_ok=True)
    EFS_DIR_FLPE.joinpath("sic4dvar").mkdir(parents=True, exist_ok=True)
    EFS_DIR_FLPE.joinpath("ssc").mkdir(parents=True, exist_ok=True)
    EFS_DIR_FLPE.joinpath("lakeflow").mkdir(parents=True, exist_ok=True)

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
    json_bucket = f"{prefix}-json"

    if reaches_of_interest:
        roi = EFS_DIR_INPUT.joinpath(reaches_of_interest)
        S3.download_file(
            config_bucket,
            reaches_of_interest,
            roi
        )
        logging.info("Downloaded %s/%s to %s", config_bucket, reaches_of_interest, EFS_DIR_INPUT.joinpath(reaches_of_interest))

        S3.upload_file(
            roi,
            json_bucket,
            reaches_of_interest,
            ExtraArgs={
                "ServerSideEncryption": "aws:kms"
            }
        )
        logging.info("Uploaded %s to %s/%s", roi, json_bucket, reaches_of_interest)

    cont_setfinder = EFS_DIR_INPUT.joinpath("continent-setfinder.json")
    S3.download_file(
        config_bucket,
        "continent-setfinder.json",
        cont_setfinder
    )
    logging.info("Downloaded %s/continent-setfinder.json to %s", config_bucket, cont_setfinder)

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

    download_directory(config_bucket, "gage", EFS_DIR_INPUT)
    download_directory(config_bucket, "sword", EFS_DIR_INPUT)
    download_directory(config_bucket, "ssc", EFS_DIR_INPUT)
    download_directory(config_bucket, "lakeflow", EFS_DIR_INPUT)
    download_directory(config_bucket, "sos", EFS_DIR_INPUT)


def download_directory(config_bucket, prefix, efs_dir):
    """Download all files located at prefix."""

    paginator = S3.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(
        Bucket=config_bucket,
        Prefix=prefix
    )

    items = []
    for page in page_iterator:
        if page.get("Contents", None):
            for content in page.get("Contents"):
                items.append(content["Key"])

    for item in items:
        efs_file = efs_dir.joinpath(item)
        if not efs_file.exists():
            efs_file.parent.mkdir(parents=True, exist_ok=True)
            S3.download_file(
                config_bucket,
                item,
                efs_file
            )
            logging.info("Downloaded %s/%s to %s", config_bucket, item, efs_file)
        else:
            logging.info("Not downloading %s", efs_file)

    if len(items) == 0:
        logging.info("No items detected for %s/%s", config_bucket, prefix)


if __name__ == "__main__":
    init_workflow(
