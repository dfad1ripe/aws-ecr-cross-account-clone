#!/usr/bin/python3
####################################################################
#
# AWS ECR smart synchronization tool
#
# (C) Dmytro Fadyeyenko
# GitHub: https://github.com/dfad1ripe/aws-crossrepo
#
####################################################################

import argparse
from datetime import date
import json
import re
import subprocess


# Default values
#
# Debug mode output is allowed - not for production usage
DEBUG = False
INFO  = True

# Exit codes
errInvalidArgument  = 1
errInvalidFile      = 2
errShell            = 11
errAWS              = 21


# Debug level printing
def debug(message):
  if DEBUG:
    print(message)

    
# Info level printing
def info(message):
  if INFO:
    print(message)

    
# Validating a value against regular expression
def validate(var, regex, errMsg, exitCode):
  debug('Validating ' + var + ' against ' + regex)
  try:
    pattern = re.compile(regex)
    if re.fullmatch(pattern, var):
      debug('Validation successfull')
    else:
      print(errMsg)
      exit(exitCode)
  except ValueError as err:
    print(err)



# Read repositories from AWS region
def getRepos(profile, region):
  info('Retrieving repos: ' + profile + ':' + region)
  cmd = 'aws ecr describe-repositories --profile ' + profile + ' --region ' + region
  debug('Running command: ' + cmd)

  p = subprocess.Popen(cmd.split(),
                       stdout = subprocess.PIPE,
                       stderr = subprocess.PIPE,
                       #stdin  = subprocess.PIPE,
                       universal_newlines = True)
  stdout, stderr = p.communicate()

  if p.returncode > 0:
    # Shell error happened
    print(stderr)
    exit(errAWS)
  else:
    debug(stdout)
    
  # Convert JSON text to a list
  j = json.loads(stdout)
  
  # Return .repositories[] property
  return j['repositories']
  

# Get list of images for AWS ECR repo
def getRepoImages(profile, region, repositoryName):
  info('Retrieving images for repository: ' + profile + ':' + region + ':' + repositoryName)
  cmd = 'aws ecr describe-images --profile ' + profile + ' --region ' + region + ' --repository-name ' + repositoryName
  debug('Running command: ' + cmd)

  p = subprocess.Popen(cmd.split(),
                       stdout = subprocess.PIPE,
                       stderr = subprocess.PIPE,
                       #stdin  = subprocess.PIPE,
                       universal_newlines = True)
  stdout, stderr = p.communicate()

  if p.returncode > 0:
    # Shell error happened
    print(stderr)
    exit(errAWS)
  else:
    debug(stdout)
  
  # Convert JSON text to a list
  j = json.loads(stdout)
  
  # Return .imageDetails[] property
  return j['imageDetails']  

  
# Calculate age of image, in calendar days
def imageAge(image):
  pushedAt = re.sub("T.*", "", image['imagePushedAt'])
  pushedDate = date.fromisoformat(pushedAt)
  return ((date.today() - pushedDate).days)
  


####################
# MAIN PROCESS
#

# Read CLI arguments
parser = argparse.ArgumentParser(description='AWS ECR smart synchronization tool.\nSee https://github.com/dfad1ripe/aws-crossrepo for the details.')
parser.add_argument('src_profile', type=str, help='Source AWS profile, as defined in ~/.aws/config')
parser.add_argument('src_region', type=str, help='Source AWS region')
parser.add_argument('dst_profile', type=str, help='Destination AWS profile, as defined in ~/.aws/config')
parser.add_argument('dst_region', type=str, help='Destination AWS region')
parser.add_argument('--days', '-d', type=int, default=30, help='How recent images to synchronize, in calendar days')
parser.add_argument('--ignore-tags', '-t', type=bool, nargs='?', default=False, const=True, help='Clone even not tagged images (default False)')
parser.add_argument('--require-scan', '-s', type=bool, nargs='?', default=False, const=True, help='Clone only scanned images (default False)')
args = parser.parse_args()

# Validating arguments
debug('Validating parameters')
validate(args.src_profile, "^[a-z0-9\-\_]+$", 'Invalid profile name: ' + args.src_profile, errInvalidArgument)
validate(args.src_region, "^[a-z0-9\-]+$", 'Invalid region name: ' + args.src_region, errInvalidArgument)
validate(args.dst_profile, "^[a-z0-9\-\_]+$", 'Invalid profile name: ' + args.dst_profile, errInvalidArgument)
validate(args.dst_region, "^[a-z0-9\-]+$", 'Invalid region name: ' + args.dst_region, errInvalidArgument)

if args.days < 1:
  print('Invalid --days value: should be 1 or more')
  exit(errInvalidArgument)

debug('')

info('Retrieving list of repositories')
repoListSrc = getRepos(args.src_profile, args.src_region)
debug(repoListSrc)
info('')

info('Retrieving list of images')
imagesToSync = []

for repo in repoListSrc:
  images = getRepoImages(args.src_profile, args.src_region, repo['repositoryName'])
  if len(images) == 0:
    info('  Repository is empty, skipping')
  else:
    for image in images:
    
      # Some images might have no tags
      try:
        tag = image['imageTags'][0]
      except NameError:
        info('  Found image: ' + image['repositoryName'] + ':' + image['imagePushedAt'])
        if not args.ignore_tags:
           info('Image is not tagged, skipping')
           continue
      except KeyError:
        info('  Found image: ' + image['repositoryName'] + ':' + image['imagePushedAt'])
        if not args.ignore_tags:
           info('Image is not tagged, skipping')
           continue
        
      info('  Found image: ' + image['repositoryName'] + ':' + tag)

      # Is image too old to be cloned?
      age = imageAge(image)
      if age > args.days:
        info('    Image is ' + str(age) + ' day(s) old, skipping')
        continue
      else:
        debug('    Image is ' + str(age) + ' day(s) old')
      
      # If we requree an image to be scanned, is it?
      if args.require_scan:
        try:
          scanStatus = image['imageScanStatus']['status']
        except NameError:
          info('    Image is not scanned, skipping')
          continue
        except KeyError:
          info('    Image is not scanned, skipping')
          continue
        info('    Image is scanned')


      imagesToSync.append(image)

info('')
info('Number of images to sync: ' + str(len(imagesToSync)))
for image in imagesToSync:
  try:
    tag = image['imageTags'][0]
  except NameError:
    info('  ' + image['repositoryName'] + ':' + image['imagePushedAt'])
  except KeyError:
    info('  ' + image['repositoryName'] + ':' + image['imagePushedAt'])
  info('  ' + image['repositoryName'] + ':' + tag)

info('')
      
print(imagesToSync)
info('')
