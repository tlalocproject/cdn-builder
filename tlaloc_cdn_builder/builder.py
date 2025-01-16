import os
import time
import json
import boto3
import hashlib

from importlib.resources import files
from botocore.exceptions import ClientError

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

# Adding functions resources
edge_functions = {
    "viewer-request": {
        "memory": 128,
        "timeout": 5,
        "runtime": "nodejs20.x",
    },
    "api-origin-request": {
        "memory": 128,
        "timeout": 5,
        "runtime": "nodejs20.x",
    },
    "s3-origin-request": {
        "memory": 128,
        "timeout": 5,
        "runtime": "nodejs20.x",
    },
    "api-origin-response": {
        "memory": 128,
        "timeout": 5,
        "runtime": "nodejs20.x",
    },
}


class builder:

    def __init__(self, config):

        # Initialize the config dictionary
        self.config = {}

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
            self.config["aws_stack_hash"] = self._get_hash(
                f"{self.config["deployer"]}/{self.config["aws_stack"]}"
            )

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

        else:

            raise ValueError("Invalid provider")

    def build(self):

        # Initialization ##########################################################

        # Reporting the configuration in use
        print(
            "Building CDN with config:\n    {}".format(
                json.dumps(self.config, indent=4).replace("\n", "\n    ")
            )
        )

        # Delete and create temporal folder
        print("Creating temporal folder")
        os.system(f"rm -rf .CDN")
        os.makedirs(".CDN", exist_ok=True)

        # Creating stack
        stack = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Parameters": {
                "parTablePermissions": {
                    "Type": "String",
                    "Default": "mytable",
                },
                "parQueueAccessLog": {
                    "Type": "String",
                    "Default": "myqueue",
                },
                "parUserPoolId": {
                    "Type": "String",
                    "Default": "mypool",
                },
            },
            "Resources": {},
            "Outputs": {},
        }

        # Functions ##############################################################

        for function in edge_functions:

            # Calculating function variable values
            edge_functions[function]["name"] = function
            function = edge_functions[function]
            function_hash = self._get_hash(
                f"{self.config["aws_stack"]}-{function["name"]}"
            )
            function["path_sources"] = files("tlaloc_cdn_builder.functions").joinpath(
                function["name"]
            )
            function_timestamp = int(os.path.getmtime(function["path_sources"]))
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
                f"zip -r .CDN/{self.config["aws_stack"]}-{function_hash}-{function_timestamp}.zip {function["path_temporal"]}/* > /dev/null"
            )

            # Deleting source folder
            print(f"{function["name"]} - Deleting source folder")
            os.system(f"rm -rf {function["path_temporal"]}")

            # Adding function resource
            print(f"{function["name"]} - Adding function resource")
            stack["Resources"][f"{function_hash}Function"] = {
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
                        "S3Key": f"CDN/{self.config["aws_stack"]}-{function_hash}-{function_timestamp}.zip",
                    },
                },
            }

            # Adding function role resource
            print(f"{function["name"]} - Adding role resource")
            stack["Resources"][f"{function_hash}FunctionRole"] = role

            # Adding function version resource
            print(f"{function["name"]} - Adding version resource")
            stack["Resources"][
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

        # Distribution ############################################################

        # Adding domain certificate resource
        stack["Resources"]["domainCertificate"] = {
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
        stack["Resources"]["bucketCloudFrontLogs"] = {
            "Type": "AWS::S3::Bucket",
            "Properties": {
                "BucketName": f"{self.config["aws_stack"]}-cloudfront-logs",
                "OwnershipControls": {
                    "Rules": [{"ObjectOwnership": "BucketOwnerPreferred"}]
                },
            },
        }

        # Adding policy for logs bucket
        stack["Resources"]["bucketCloudFrontLogsPolicy"] = {
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
                                        "Fn::Sub": "arn:aws:cloudfront::${AWS::AccountId}:distribution/asdf"
                                    }
                                }
                            },  # ${cloudFrontDistribution}"
                        }
                    ]
                },
            },
        }

        stack["Resources"]["cloudFrontDistribution"] = {
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

        stack["Resources"]["cloudFrontOriginAccessControl"] = {
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

        stack["Resources"]["cloudFrontDistributionDNSRecord"] = {
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

        # Origins #################################################################

        origin_id = 0
        for origin in self.config["aws_origins"]:

            if origin["type"] == "s3":
                if origin["owner"] == "self":
                    stack["Resources"][f"distributionOrigin{origin_id:03}Bucket"] = {
                        "Type": "AWS::S3::Bucket",
                        "Properties": {
                            "BucketName": {
                                "Fn::Sub": origin["name"],
                            }
                        },
                    }
                    stack["Resources"][
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
                    stack["Resources"]["cloudFrontDistribution"]["Properties"][
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
                    stack["Resources"]["cloudFrontDistribution"]["DependsOn"].append(
                        f"distributionOrigin{origin_id:03}Bucket"
                    )
                else:
                    raise ValueError("Invalid origin owner")
            elif origin["type"] == "apigateway":
                stack["Resources"]["cloudFrontDistribution"]["Properties"][
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
                stack["Resources"]["cloudFrontDistribution"]["Properties"][
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
                        "LambdaFunctionAssociations": [
                            {
                                "EventType": "viewer-request",
                                "LambdaFunctionARN": {
                                    "Fn::Sub": f'${{{edge_functions["viewer-request"]["version"]}.FunctionArn}}'
                                },
                                "IncludeBody": True,
                            },
                            {
                                "EventType": "origin-request",
                                "LambdaFunctionARN": {
                                    "Fn::Sub": f'${{{edge_functions["api-origin-request"]["version"]}.FunctionArn}}'
                                },
                                "IncludeBody": True,
                            },
                            {
                                "EventType": "origin-response",
                                "LambdaFunctionARN": {
                                    "Fn::Sub": f'${{{edge_functions["api-origin-response"]["version"]}.FunctionArn}}'
                                },
                            },
                        ],
                    }
                )

            if "default" in origin and origin["default"]:
                if origin["type"] == "s3":
                    stack["Resources"]["cloudFrontDistribution"]["Properties"][
                        "DistributionConfig"
                    ]["DefaultCacheBehavior"] = {
                        "TargetOriginId": f"distributionOrigin{origin_id:03}Bucket",
                        "Compress": True,
                        "ViewerProtocolPolicy": "redirect-to-https",
                        "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",
                        "OriginRequestPolicyId": "b689b0a8-53d0-40ab-baf2-68738e2966ac",
                        "LambdaFunctionAssociations": [
                            {
                                "EventType": "viewer-request",
                                "LambdaFunctionARN": {
                                    "Fn::Sub": f'${{{edge_functions["viewer-request"]["version"]}.FunctionArn}}'
                                },
                                "IncludeBody": True,
                            },
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
            origin_id += 1

        # Dump ####################################################################

        # Save stack
        print("Saving stack")
        with open(
            f".CDN/{self.config["aws_stack"]}-{self.config["timestamp"]}.json", "w"
        ) as file:
            file.write(json.dumps(stack, indent=4))

    def deploy(self):

        # Setting the profile and oppening s3 client
        self.aws = boto3.Session(profile_name=self.config["aws_profile"])

        # Uploading files to S3
        print("Uploading files to S3")
        self._upload_files_to_s3("us-east-1")

        # Deploying stack
        print("Deploying stack")
        self._deploy_cloudformation("us-east-1")

        del self.aws

    def _upload_files_to_s3(self, region):

        s3_client = self.aws.client("s3")

        print(f"Uploading files")
        for file in os.listdir(f".CDN/"):
            print(f"Uploading {file}")
            s3_client.upload_file(
                f".CDN/{file}",
                self.config["aws_bucket"],
                f"CDN/{file}",
            )

        s3_client.close()

    def _deploy_cloudformation(self, region):

        # Create the CloudFormation client
        self.cloudformation_client = self.aws.client(
            "cloudformation", region_name=region
        )

        # Check the aws_stack status
        aws_stack_status = self._check_aws_stack(self.config["aws_stack"])
        print(f"Stack status: {aws_stack_status}")

        # Handle the aws_stack
        aws_bucket = self.config["aws_bucket"]
        if aws_stack_status == "DOES_NOT_EXIST":
            print("Creating aws_stack")
            self.cloudformation_client.create_stack(
                StackName=self.config["aws_stack"],
                TemplateURL=f"https://{aws_bucket}.s3.amazonaws.com/CDN/{self.config["aws_stack"]}-{self.config["timestamp"]}.json",
                Capabilities=["CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"],
            )
        elif aws_stack_status in successful_statuses:
            try:
                print("Updating aws_stack")
                self.cloudformation_client.update_stack(
                    StackName=self.config["aws_stack"],
                    TemplateURL=f"https://{aws_bucket}.s3.amazonaws.com/CDN/{self.config["aws_stack"]}-{self.config["timestamp"]}.json",
                    Capabilities=["CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"],
                )
            except ClientError as e:
                if "No updates are to be performed" in str(e):
                    print("No updates detected. Skipping stack update.")
                else:
                    raise
        elif (
            aws_stack_status in failed_statuses or aws_stack_status in rollback_statuses
        ):
            print("Handling failed aws_stack")
            self.cloudformation_client.delete_stack(StackName=self.config["aws_stack"])
            waiter = self.cloudformation_client.get_waiter("stack_delete_complete")
            waiter.wait(
                StackName=self.config["aws_stack"],
                WaiterConfig={
                    "Delay": 1,  # Check every 1 seconds
                    "MaxAttempts": 120,  # Retry up to 120 times
                },
            )
            print("Creating aws_stack")
            self.cloudformation_client.create_stack(
                StackName=self.config["aws_stack"],
                TemplateURL=f"https://{aws_bucket}.s3.amazonaws.com/CDN/{self.config["aws_stack"]}-{self.config["timestamp"]}.json",
                Capabilities=["CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"],
            )
        elif aws_stack_status in in_progress_statuses:
            raise ValueError("Stack is in progress")

        # Close the CloudFormation client
        self.cloudformation_client.close()

    def _get_hash(self, string):
        return hashlib.md5(string.encode()).hexdigest()

    def _check_aws_stack(self, name):

        try:
            response = self.cloudformation_client.describe_stacks(StackName=name)
            return response.get("Stacks")[0].get("StackStatus")
        except ClientError as e:
            if "does not exist" in str(e):
                return "DOES_NOT_EXIST"
            else:
                raise
