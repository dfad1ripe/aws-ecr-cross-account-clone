# ToDo list #

## Repositories to be created at destination with same scan enforce flag as in source ##

Currently, this value is enforced to true. Should match the settings of the repo with the same name in source AWS account.

## Report which images were synced and which were failed ##

Currently, only numbers are reported

## Limit number of threads running simultaneously ##

If we have dozens, or hundreds of images to clone, we should not start as many threads in parallel. Instead, we should limit the number of threads, adding new threads when old threads complete and join.

## Docker functions to be optimized ##

These functions reuse the same code. This code should be moved to standalone function.