import os
import time

in_progress_statuses = [
    "CREATE_IN_PROGRESS",
    "ROLLBACK_IN_PROGRESS",
    "DELETE_IN_PROGRESS",
    "UPDATE_IN_PROGRESS",
    "UPDATE_ROLLBACK_IN_PROGRESS",
    "REVIEW_IN_PROGRESS",
    "IMPORT_IN_PROGRESS",
    "IMPORT_ROLLBACK_IN_PROGRESS",
]

# Successful statuses
successful_statuses = [
    "CREATE_COMPLETE",
    "DELETE_COMPLETE",
    "UPDATE_COMPLETE",
    "UPDATE_ROLLBACK_COMPLETE",
    "IMPORT_COMPLETE",
    "IMPORT_ROLLBACK_COMPLETE",
]

# Failed statuses
failed_statuses = [
    "CREATE_FAILED",
    "ROLLBACK_FAILED",
    "DELETE_FAILED",
    "UPDATE_FAILED",
    "UPDATE_ROLLBACK_FAILED",
    "IMPORT_FAILED",
    "IMPORT_ROLLBACK_FAILED",
]

# Rollback statuses
rollback_statuses = [
    "ROLLBACK_COMPLETE",
    "UPDATE_ROLLBACK_COMPLETE",
    "IMPORT_ROLLBACK_COMPLETE",
]

# Special cases
special_cases = ["DELETE_IN_PROGRESS", "DELETE_COMPLETE", "DELETE_FAILED"]


class builder:

    def __init__(self, config):

        # Initialize the config dictionary
        self.config = {}

        # Checking common config parameters #######################################
        # Checking if the config is a dictionary
        if not isinstance(config, dict):
            raise ValueError("Config must be a dictionary")

        # Checking the config.name parameter
        if (
            not config.get("name")
            or not isinstance(config["name"], str)
            or not config["name"].strip()
        ):
            raise ValueError("Config must be a non empty string parameter name")
        self.config["name"] = config["name"]

        # Checking the deployer parameter
        if (
            not config.get("deployer")
            or not isinstance(config["deployer"], str)
            or not config["deployer"].strip()
        ):
            raise ValueError(
                "Config must have a non empty string parameter named deployer"
            )
        self.config["deployer"] = config["deployer"]

        # Checking the provider parameter
        if (
            not config.get("provider")
            or not isinstance(config["provider"], str)
            or not config["provider"].strip()
        ):
            raise ValueError(
                "Config must have a non empty string parameter named provider"
            )
        self.config["provider"] = config["provider"]

        # Storing timestamp
        self.config["timestamp"] = int(time.time())

        # Checking the AWS deployment parameters ##################################
        if self.config["provider"] == "aws":

            # Checking the aws_profile parameter
            if (
                not config.get("aws_profile")
                or not isinstance(config["aws_profile"], str)
                or not config["aws_profile"].strip()
            ):
                raise ValueError(
                    "Config must be a non empty string parameter aws_profile"
                )
            self.config["aws_profile"] = config["aws_profile"]

            # Checking the aws_region parameter
            if (
                not config.get("aws_region")
                or not isinstance(config["aws_region"], str)
                or not config["aws_region"].strip()
            ):
                raise ValueError(
                    "Config must be a non empty string parameter aws_region"
                )
            self.config["aws_region"] = config["aws_region"]

            # Checking the aws_bucket parameter
            if (
                not config.get("aws_bucket")
                or not isinstance(config["aws_bucket"], str)
                or not config["aws_bucket"].strip()
            ):
                raise ValueError(
                    "Config must be a non empty string parameter aws_bucket"
                )
            self.config["aws_bucket"] = config["aws_bucket"]

            # Checking the aws_stack parameter
            if (
                not config.get("aws_stack")
                or not isinstance(config["aws_stack"], str)
                or not config["aws_stack"].strip()
            ):
                raise ValueError(
                    "Config must be a non empty string parameter aws_stack"
                )
            self.config["aws_stack"] = config["aws_stack"]
            self.config["aws_stack_hash"] = self._get_hash(
                f"{self.config["deployer"]}/{self.config["aws_stack"]}"
            )

        else:
            raise ValueError("Invalid provider")
