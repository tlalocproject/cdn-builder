import os
import time
import json
import boto3

from importlib.resources import files
from tlaloc_commons import commons  # type: ignore
from .edge_functions import edge_functions


class builder:
    """
    This class is used to build and deploy a CDN

    Parameters:
        config (dict): A dictionary with the following parameters:
            deployer (str): The name of the deployer
            provider (str): The name of the provider if set to aws, the following parameters are required:

                aws_profile (str): The name of the AWS profile to use
                aws_stack (str): The name of the stack
                aws_stack_hash (str): The hash of the stack
                aws_region (str): The AWS region to use
                aws_bucket (str): The name of the S3 bucket to use
                aws_domain (str): The domain name to use
                aws_hosted_zone_id (str): The hosted zone id to use
                aws_origins (list): A list of origins to use

    Raises:
        ValueError: If the config parameter is not a dictionary
        ValueError: If the config parameter does not have a deployer parameter
        ValueError: If the config parameter does not have a provider parameter
        ValueError: If the config parameter does not have a aws_profile parameter
        ValueError: If the config parameter does not have a aws_stack parameter
        ValueError: If the config parameter does not have a aws_stack_hash parameter
        ValueError: If the config parameter does not have a aws_region parameter
        ValueError: If the config parameter does not have a aws_bucket parameter
        ValueError: If the config parameter does not have a aws_domain parameter
        ValueError: If the config parameter does not have a aws_hosted_zone_id parameter
        ValueError: If the config parameter does not have a aws_origins parameter
        ValueError: If the aws_region parameter is not us-east-1
        ValueError: If the provider parameter is not aws
    """

    def __init__(self, config):

        # Initialize the config dictionary
        self.config = {}
        self.built = False
        self.deployed = False

        # Checking common config parameters #######################################

        # Checking if the config is a dictionary
        if not isinstance(config, dict):
            raise ValueError("Config must be a dictionary")

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

            # Checking the aws_stack parameter
            if (
                not config.get("aws_stack_hash")
                or not isinstance(config["aws_stack_hash"], str)
                or not config["aws_stack_hash"].strip()
            ):
                raise ValueError(
                    "Config must be a non empty string parameter aws_stack_hash"
                )
            self.config["aws_stack_hash"] = config["aws_stack_hash"]

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
            if config["aws_region"] != "us-east-1":
                raise ValueError("aws_region can only be us-east-1")
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

            # Checking the aws_domain parameter
            if (
                not config.get("aws_domain")
                or not isinstance(config["aws_domain"], str)
                or not config["aws_domain"].strip()
            ):
                raise ValueError(
                    "Config must be a non empty string parameter aws_domain"
                )
            self.config["aws_domain"] = config["aws_domain"]

            # Checking the aws_hosted_zone_id parameter
            if (
                not config.get("aws_hosted_zone_id")
                or not isinstance(config["aws_hosted_zone_id"], str)
                or not config["aws_hosted_zone_id"].strip()
            ):
                raise ValueError(
                    "Config must be a non empty string parameter aws_hosted_zone_id"
                )
            self.config["aws_hosted_zone_id"] = config["aws_hosted_zone_id"]

            # Checking the aws_origins parameter
            if (
                not config.get("aws_origins")
                or not isinstance(config["aws_origins"], list)
                or not config["aws_origins"]
            ):
                raise ValueError(
                    "Config must be a non empty list parameter aws_origins"
                )
            self.config["aws_origins"] = config["aws_origins"]
            self.config["aws_folder"] = "CDN"

        else:

            raise ValueError("Invalid provider")

    def build(self):
        """
        This function builds the CDN preparing the files

        Parameters:
            None

        Returns:
            None

        Raises:
            ValueError: If the provider is not supported
        """

        if self.config["provider"] == "aws":

            self._aws_build()

        else:

            raise ValueError("Invalid provider")

        # Set the built flag to True
        self.built = True

    def _aws_build(self):
        """
        This function builds and AWS CDN preparing the files and the CloudFormation template

        Parameters:
            None

        Returns:
            None

        Raises:
            ValueError:
        """

        # Initialization ##########################################################

        # Reporting the configuration in use
        print(
            "Building CDN with config:\n    {}".format(
                json.dumps(self.config, indent=4).replace("\n", "\n    ")
            )
        )

        # Checking the number of default origins
        default_origins = [
            origin for origin in self.config["aws_origins"] if origin.get("default")
        ]
        if len(default_origins) != 1:
            raise ValueError(
                "Exactly one origin must have the 'default' flag set to true"
            )

        # Delete and create temporal folder
        print("Creating temporal folder")
        os.system(f"rm -rf .CDN")
        os.makedirs(".CDN", exist_ok=True)

        # Creating base template
        template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Parameters": {
                "parTablePermissions": {
                    "Type": "String",
                    "Default": "my_table",
                },
                "parQueueAccessLog": {
                    "Type": "String",
                    "Default": "my_queue",
                },
                "parUserPoolId": {
                    "Type": "String",
                    "Default": "my_pool",
                },
            },
            "Resources": {},
            "Outputs": {},
        }

        # Building Functions ######################################################

        for function in edge_functions:

              # Calculating function variable values
            edge_functions[function]["name"] = function
            function = edge_functions[function]
            function_hash = commons.get_hash(
                f"{self.config["aws_stack"]}-{function["name"]}"
            )
            function["path_sources"] = files("tlaloc_cdn_builder.functions").joinpath(
                function["name"]
            )
            function_timestamp = int(
                os.path.getmtime(f'{function["path_sources"]}/index.mjs')
            )
            function["path_temporal"] = f".CDN/{function_hash}"
            role = json.load(open(os.path.join(function["path_sources"], "role.json")))

            # Copying function files
            print(f"{function["name"]} - Copying files")
            os.system(f"cp -r {function["path_sources"]} {function["path_temporal"]}")
            os.system(f"rm {function["path_temporal"]}/role.json")

            # Installing dependencies
            print(f"{function["name"]} - Installing dependencies")
            return_value = os.system(
                f"npm install --prefix {function['path_temporal']} > {function['path_temporal']}/package.log 2>&1"
            )
            if return_value != 0:
                raise ValueError(f"Error building {function["name"]} function")

            # Cleaning up folder
            print(f"{function["name"]} - Cleaning up folder")
            os.system(f"rm -rf {function["path_temporal"]}/package*")

            # Zipping the source code
            print(f"{function["name"]} - Zipping the source code")
            os.system(
                f"cd {function['path_temporal']} && zip -r ../../.CDN/{function_timestamp}-{function_hash}-{self.config['aws_region']}.zip . > /dev/null"
            )

            # Deleting source folder
            print(f"{function["name"]} - Deleting source folder")
            os.system(f"rm -rf {function["path_temporal"]}")

            # Adding function resource
            print(f"{function["name"]} - Adding function resource")
            template["Resources"][f"{function_hash}Function"] = {
                "Type": "AWS::Lambda::Function",
                "Properties": {
                    "FunctionName": f"{function_hash}-{function["name"]}",
                    "Handler": "index.handler",
                    "Role": {"Fn::GetAtt": [f"{function_hash}FunctionRole", "Arn"]},
                    "Runtime": function["runtime"],
                    "Timeout": function["timeout"],
                    "MemorySize": function["memory"],
                    "Code": {
                        "S3Bucket": self.config["aws_bucket"],
                        "S3Key": f"CDN/{function_timestamp}-{function_hash}-{self.config["aws_region"]}.zip",
                    },
                },
            }

            # Adding function role resource
            print(f"{function["name"]} - Adding role resource")
            template["Resources"][f"{function_hash}FunctionRole"] = role

            # Adding function version resource
            print(f"{function["name"]} - Adding version resource")
            template["Resources"][
                f"{function_hash}FunctionVersion{function_timestamp}"
            ] = {
                "Type": "AWS::Lambda::Version",
                "DependsOn": f"{function_hash}Function",
                "DeletionPolicy": "Retain",
                "Properties": {
                    "FunctionName": {"Ref": f"{function_hash}Function"},
                },
            }
            function["version"] = f"{function_hash}FunctionVersion{function_timestamp}"

        # Building Distribution ###################################################

        # Adding domain certificate resource
        template["Resources"]["domainCertificate"] = {
            "Type": "AWS::CertificateManager::Certificate",
            "Properties": {
                "DomainName": self.config["aws_domain"],
                "DomainValidationOptions": [
                    {
                        "DomainName": self.config["aws_domain"],
                        "HostedZoneId": self.config["aws_hosted_zone_id"],
                    }
                ],
                "ValidationMethod": "DNS",
            },
        }

        # Adding logs bucket
        template["Resources"]["bucketCloudFrontLogs"] = {
            "Type": "AWS::S3::Bucket",
            "Properties": {
                "BucketName": f"{self.config["deployer"]}-weelock-cloudfront-logs-{self.config["aws_region"]}",
                "OwnershipControls": {
                    "Rules": [{"ObjectOwnership": "BucketOwnerPreferred"}]
                },
            },
        }

        # Adding policy for logs bucket
        template["Resources"]["bucketCloudFrontLogsPolicy"] = {
            "Type": "AWS::S3::BucketPolicy",
            "Properties": {
                "Bucket": {"Ref": "bucketCloudFrontLogs"},
                "PolicyDocument": {
                    "Statement": [
                        {
                            "Action": "s3:PutObject",
                            "Effect": "Allow",
                            "Resource": {"Fn::Sub": "${bucketCloudFrontLogs.Arn}/*"},
                            "Principal": {"Service": "cloudfront.amazonaws.com"},
                            "Condition": {
                                "StringEquals": {
                                    "AWS:SourceArn": {
                                        "Fn::Sub": "arn:aws:cloudfront::${AWS::AccountId}:distribution/${cloudFrontDistribution}"
                                    }
                                }
                            },
                        }
                    ]
                },
            },
        }

        # Adding distribution resource
        template["Resources"]["cloudFrontDistribution"] = {
            "Type": "AWS::CloudFront::Distribution",
            "DependsOn": ["bucketCloudFrontLogs"],
            "Properties": {
                "DistributionConfig": {
                    "Origins": [],
                    "Enabled": True,
                    "DefaultRootObject": "index.html",
                    "CacheBehaviors": [],
                    "HttpVersion": "http2",
                    "IPV6Enabled": True,
                    "Aliases": [
                        self.config["aws_domain"],
                    ],
                    "Logging": {
                        "Bucket": {"Fn::GetAtt": ["bucketCloudFrontLogs", "DomainName"]}
                    },
                    "DefaultRootObject": "index.html",
                    "PriceClass": "PriceClass_All",
                    "ViewerCertificate": {
                        "AcmCertificateArn": {"Ref": "domainCertificate"},
                        "MinimumProtocolVersion": "TLSv1.2_2021",
                        "SslSupportMethod": "sni-only",
                    },
                }
            },
        }

        # Adding origin access control resource for s3 origins
        template["Resources"]["cloudFrontOriginAccessControl"] = {
            "Type": "AWS::CloudFront::OriginAccessControl",
            "Properties": {
                "OriginAccessControlConfig": {
                    "Name": f"{self.config["aws_stack"]}-cloudfront-oac",
                    "OriginAccessControlOriginType": "s3",
                    "SigningBehavior": "always",
                    "SigningProtocol": "sigv4",
                }
            },
        }

        # Adding DNS record for distribution
        template["Resources"]["cloudFrontDistributionDNSRecord"] = {
            "Type": "AWS::Route53::RecordSet",
            "Properties": {
                "HostedZoneId": self.config["aws_hosted_zone_id"],
                "Name": self.config["aws_domain"],
                "Type": "CNAME",
                "TTL": "300",
                "ResourceRecords": [
                    {"Fn::GetAtt": ["cloudFrontDistribution", "DomainName"]}
                ],
            },
        }

        # Building Origins ########################################################

        origin_id = 0
        for origin in self.config["aws_origins"]:

            # Adding origin resources of type s3
            if origin["type"] == "s3":
                if "owner" in origin and origin["owner"] == "self":
                    template["Resources"][f"distributionOrigin{origin_id:03}Bucket"] = {
                        "Type": "AWS::S3::Bucket",
                        "Properties": {"BucketName": origin["name"]},
                    }
                    template["Resources"][
                        f"distributionOrigin{origin_id:03}BucketPolicy"
                    ] = {
                        "Type": "AWS::S3::BucketPolicy",
                        "Properties": {
                            "Bucket": {
                                "Ref": f"distributionOrigin{origin_id:03}Bucket"
                            },
                            "PolicyDocument": {
                                "Statement": [
                                    {
                                        "Action": "s3:GetObject",
                                        "Effect": "Allow",
                                        "Resource": {
                                            "Fn::Sub": f"${{{f"distributionOrigin{origin_id:03}Bucket"}.Arn}}/*"
                                        },
                                        "Principal": {
                                            "Service": "cloudfront.amazonaws.com"
                                        },
                                        "Condition": {
                                            "StringEquals": {
                                                "AWS:SourceArn": {
                                                    "Fn::Sub": "arn:aws:cloudfront::${AWS::AccountId}:distribution/${cloudFrontDistribution}"
                                                }
                                            }
                                        },
                                    }
                                ]
                            },
                        },
                    }
                    template["Resources"]["cloudFrontDistribution"]["Properties"][
                        "DistributionConfig"
                    ]["Origins"].append(
                        {
                            "Id": f"distributionOrigin{origin_id:03}Bucket",
                            "DomainName": {
                                "Fn::GetAtt": [
                                    f"distributionOrigin{origin_id:03}Bucket",
                                    "RegionalDomainName",
                                ]
                            },
                            "S3OriginConfig": {"OriginAccessIdentity": ""},
                            "OriginAccessControlId": {
                                "Fn::GetAtt": ["cloudFrontOriginAccessControl", "Id"]
                            },
                        }
                    )
                    template["Resources"]["cloudFrontDistribution"]["DependsOn"].append(
                        f"distributionOrigin{origin_id:03}Bucket"
                    )
                else:
                    template["Resources"]["cloudFrontDistribution"]["Properties"][
                        "DistributionConfig"
                    ]["Origins"].append(
                        {
                            "Id": f"distributionOrigin{origin_id:03}Bucket",
                            "DomainName": f"{origin["name"]}.s3.amazonaws.com",
                            "S3OriginConfig": {"OriginAccessIdentity": ""},
                            "OriginAccessControlId": {
                                "Fn::GetAtt": ["cloudFrontOriginAccessControl", "Id"]
                            },
                        }
                    )

            # Adding origin resources of type apigateway
            elif origin["type"] == "apigateway":
                template["Resources"]["cloudFrontDistribution"]["Properties"][
                    "DistributionConfig"
                ]["Origins"].append(
                    {
                        "Id": f"distributionOrigin{origin_id:03}Api",
                        "DomainName": origin["domain_name"],
                        "CustomOriginConfig": {
                            "HTTPPort": 80,
                            "HTTPSPort": 443,
                            "OriginProtocolPolicy": "https-only",
                        },
                    }
                )
                template["Resources"]["cloudFrontDistribution"]["Properties"][
                    "DistributionConfig"
                ]["CacheBehaviors"].append(
                    {
                        "TargetOriginId": f"distributionOrigin{origin_id:03}Api",
                        "PathPattern": origin["mask"],
                        "Compress": False,
                        "ViewerProtocolPolicy": "https-only",
                        "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",
                        "OriginRequestPolicyId": "b689b0a8-53d0-40ab-baf2-68738e2966ac",
                        "AllowedMethods": [
                            "GET",
                            "HEAD",
                            "OPTIONS",
                            "PUT",
                            "PATCH",
                            "POST",
                            "DELETE",
                        ],
                        # "LambdaFunctionAssociations": [
                        #     {
                        #         "EventType": "viewer-request",
                        #         "LambdaFunctionARN": {
                        #             "Fn::Sub": f'${{{edge_functions["viewer-request"]["version"]}.FunctionArn}}'
                        #         },
                        #         "IncludeBody": True,
                        #     },
                        #     {
                        #         "EventType": "origin-request",
                        #         "LambdaFunctionARN": {
                        #             "Fn::Sub": f'${{{edge_functions["api-origin-request"]["version"]}.FunctionArn}}'
                        #         },
                        #         "IncludeBody": True,
                        #     },
                        #     {
                        #         "EventType": "origin-response",
                        #         "LambdaFunctionARN": {
                        #             "Fn::Sub": f'${{{edge_functions["api-origin-response"]["version"]}.FunctionArn}}'
                        #         },
                        #     },
                        # ],
                    }
                )

            # Adding default cache behavior
            if "default" in origin and origin["default"]:
                if origin["type"] == "s3":
                    template["Resources"]["cloudFrontDistribution"]["Properties"][
                        "DistributionConfig"
                    ]["DefaultCacheBehavior"] = {
                        "TargetOriginId": f"distributionOrigin{origin_id:03}Bucket",
                        "Compress": True,
                        "ViewerProtocolPolicy": "redirect-to-https",
                        "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",
                        "OriginRequestPolicyId": "b689b0a8-53d0-40ab-baf2-68738e2966ac",
                        "LambdaFunctionAssociations": [
                            #     {
                            #         "EventType": "viewer-request",
                            #         "LambdaFunctionARN": {
                            #             "Fn::Sub": f'${{{edge_functions["viewer-request"]["version"]}.FunctionArn}}'
                            #         },
                            #         "IncludeBody": True,
                            #     },
                            {
                                "EventType": "origin-request",
                                "LambdaFunctionARN": {
                                    "Fn::GetAtt": [
                                        edge_functions["s3-origin-request"]["version"],
                                        "FunctionArn",
                                    ]
                                },
                                "IncludeBody": True,
                            },
                        ],
                    }
                else:
                    raise ValueError("Invalid origin type for default origin")

            origin_id += 1

        template["Outputs"]["cloudFrontDistribution"] = {
            "Value": {"Ref": "cloudFrontDistribution"},
            "Export": {"Name": f"{self.config["deployer"]}-cloudFrontDistribution"},
        }
        # Creating the template file ##############################################

        # Save stack
        print("Saving template")
        json.dump(
            template,
            indent=4,
            sort_keys=True,
            fp=open(
                f".CDN/{self.config["timestamp"]}-{self.config["aws_stack_hash"]}-{self.config["aws_region"]}.json",
                "w",
            ),
        )

        self.config["aws_template_file"] = (
            f"{self.config["timestamp"]}-{self.config["aws_stack_hash"]}-{self.config["aws_region"]}.json"
        )

    def deploy(self, wait=False):
        """
        This function deploys the CDN using the provider specified in the config

        Parameters:
            None

        Returns:
            None

        Raises:
            ValueError: If the CDN has not been built
            ValueError: If the provider is not supported
        """

        if not self.built:

            raise ValueError("You must build the CDN before deploying it")

        if self.config["provider"] == "aws":

            self._aws_deploy(wait)

        else:

            raise ValueError("Invalid provider")

        # Set the deployed flag to True
        self.deployed = True

    def _aws_deploy(self, wait=False):
        """
        This function deploys an AWS CDN using the CloudFormation template and files created by build

        Parameters:
            None

        Returns:
            None
        """

        # Setting the profile and opening s3 client
        self.aws = boto3.Session(profile_name=self.config["aws_profile"])

        # Uploading files to S3
        print("Uploading files to S3")
        self._aws_upload()

        # Deploying stack
        print("Deploying stack")
        print(json.dumps(self.config, indent=4))
        commons.aws.cloudformation.deploy(self, capabilities=["CAPABILITY_IAM"])

        # Wait for the deployment to finish
        if wait:
            print("Waiting for the deployment to finish")
            commons.aws.cloudformation.deploy_wait(self)

        # Deletes the session
        del self.aws

    def _aws_upload(self):
        """
        This function uploads the required files to the S3 bucket

        Parameters:
            None

        Returns:
            None
        """

        # Creating the s3 client
        s3_client = self.aws.client("s3")

        # Uploading files
        print(f"Uploading files")
        for file in os.listdir(f".CDN/"):
            if file.endswith(".zip"):
                print(f"Uploading {file}")
                s3_client.upload_file(
                    f".CDN/{file}",
                    self.config["aws_bucket"],
                    f"CDN/{file}",
                )

        # Upload the API template to S3
        s3_client.upload_file(
            f".CDN/{self.config["timestamp"]}-{self.config["aws_stack_hash"]}-{self.config["aws_region"]}.json",
            self.config["aws_bucket"],
            f"CDN/{self.config["timestamp"]}-{self.config["aws_stack_hash"]}-{self.config["aws_region"]}.json",
        )

        # Closing the s3 client
        s3_client.close()
