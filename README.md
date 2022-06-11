# AWS ECR Cross-Account Clone Tool #

This tool allows to clone ECR repositories between independent AWS accounts, when direct mirroring is not allowed by access policies, or when smart cloning rules should be applied.

It uses a host in the middle, that has access to both AWS accounts, and runs docker to pull-push images.

## Prerequisites ##

The following packages should be installed on the machine and be accessible with PATH variable:

- Python 3.5+ with basic set of modules.
- aws CLI 2.0+ binary.
- docker binary, all recent versions should work.

The tool was tested with Python 3.9.7, aws-cli 2.7.1 and docker 20.10.16.

## Initial AWS setup ##

You need to have access to both 'source' and 'destination' AWS accounts. IAM policies should allow at least read access to the 'source' ECR and write access to the 'destination' ECR.

Particularly, in the 'source' repository, at least the following actions should be allowed by IAM policies for the actual IAM user or role:

- ecr:DescribeImages
- ecr:DescribeRepositories
- ecr:ListImages
- ecr:GetRegistryScanningConfiguration

Correspondingly, in the 'target' repository, at least the following actions should be allowed by IAM policies for the actual IAM user or role:

- ecr:DescribeImages
- ecr:DescribeRepositories
- ecr:ListImages
- ecr:PutImage
- ecr:InitiateLayerUpload
- ecr:UploadLayerPart
- ecr:CompleteLayerUpload
- ecr:BatchCheckLayerAvailability

Additionally, identity-based IAM policy for the actual IAM user or role in both accounts should allow the following actions for "*" resource:

- ecr:GetAuthorizationToken (necessary to run `docker login`)
- ecr:DescribeImageScanFindings (necessary to retrieve scan results)


Your `~/.aws/credentials` file should define separate profiles for both 'source' and 'destination' AWS accounts. Example of setup:

`~/.aws/credentials`:

    [src]
    aws_access_key_id = <key_id_src>
    aws_secret_access_key = <key_scr>
    region = us-east-1
    [dst]
    aws_access_key_id = <key_id_dst>
    aws_secret_access_key = <key_dst>
    region = us-west-2

where the values in angle brackets are your actual access credentials for corresponding AWS accounts.

## Syntax ##

usage: aws_crossrepo.py [-h] [--days DAYS] [--ignore-tags [IGNORE_TAGS]] [--require-scan [REQUIRE_SCAN]] src_profile src_region dst_profile dst_region

AWS ECR smart synchronization tool. See https://github.com/dfad1ripe/aws-crossrepo for the details.

positional arguments:

    src_profile           Source AWS profile, as defined in ~/.aws/config
    src_region            Source AWS region
    dst_profile           Destination AWS profile, as defined in ~/.aws/config
    dst_region            Destination AWS region

optional arguments:

    -h, --help                                          show this help message and exit
    --days DAYS, -d DAYS                                How recent images to synchronize, in calendar days
    --ignore-tags [IGNORE_TAGS], -t [IGNORE_TAGS]       Clone even not tagged images (default False)
    --require-scan [REQUIRE_SCAN], -s [REQUIRE_SCAN]    Clone only scanned images (default False)
