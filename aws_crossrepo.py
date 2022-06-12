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
import threading


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
errDocker           = 22


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

  
# Retrieve credentials for ECR repository  
def getECRCredentials(profile, region):
  info('Retrieving credentials for: ' + profile + ':' + region)
  cmd = 'aws ecr get-login-password --region ' + region + ' --profile ' + profile

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
    return stdout.rstrip()

    
# Docker login
def dockerLogin(FQDN, password):
  info('Docker login to: ' + FQDN)
  debug('  using password: ' + password)
  cmd = 'docker login --username AWS --password ' + password + ' ' + FQDN

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
    exit(errDocker)
  else:
    print(stdout)

    
# Build ECR FQDN for profile
# arguments:
#   - AWS profile
#   - AWS region
# returns: FQDN for ECR in this profile and region
def buildFQDN(profile, region):
  info('Generating ECR FQDN for profile: ' + profile)
  cmd = 'aws ecr describe-registry --profile ' + profile

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
  
  accountId = j['registryId']
  return str(accountId) + '.dkr.ecr.' + region + '.amazonaws.com'


  
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
      except (NameError, KeyError) as e:
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
        except (NameError, KeyError) as e:
          info('    Image is not scanned, skipping')
          continue
        info('    Image is scanned')


      imagesToSync.append(image)

info('')
info('Number of images to sync: ' + str(len(imagesToSync)))
for image in imagesToSync:
  try:
    tag = image['imageTags'][0]
  except (NameError, KeyError) as e:
    info('  ' + image['repositoryName'] + ':' + image['imagePushedAt'])
  info('  ' + image['repositoryName'] + ':' + tag)

info('')
      
#print(imagesToSync)
#info('')

# Build FQDN for Dst repo
fqdnDst = buildFQDN(args.dst_profile, args.dst_region)

# Multithreading execution of docker login
#
# Initial structures
threads = []
threadsLogged = 0

# Defining thread class
class loginThread(threading.Thread):
  def __init__(self, name, profile, region, FQDN):
    threading.Thread.__init__(self)
    self.name = name
    self.profile = profile
    self.region = region
    self.FQDN = FQDN
  def run(self):
    global threadsLogged
    debug('Starting thread: ' + self.name)
    self.creds = getECRCredentials(self.profile, self.region)
    dockerLogin(self.FQDN, self.creds)
    threadsLogged = threadsLogged + 1
    debug('Exiting thread ' + self.name)

# Defining and running threads    
loginThreadSrc = loginThread('login thread for source repository',
                             args.src_profile,
                             args.src_region,
                             re.sub("\/.*", "", repoListSrc[0]['repositoryUri']))
loginThreadSrc.start()
threads.append(loginThreadSrc)

loginThreadDst = loginThread('login thread for destination repository',
                             args.dst_profile,
                             args.dst_region,
                             fqdnDst)
loginThreadDst.start()
threads.append(loginThreadDst)

# Waiting for all threads to complete
for t in threads:
    t.join()
debug('Multithreading part complete')

# Check if docker login was successful for both repositories
print('Successful login happened in ' + str(threadsLogged) + ' threads of 2')
if threadsLogged < 2:
  print('Docker was not able to login. Please review the messages below and fix the error.')
  exit(errDocker)
  
