#!/bin/bash


helpFunction()
{
   echo ""
   echo "Usage: $0 collector_directory_name --upload "
   echo "Usage: $0 collector_directory_name"
   echo "Usage: $0 --help \n $0 -h"
   exit 1 # Exit script after printing help
}

if [ -z "$1" ]
then
   echo "please enter collector directory_name ";
   helpFunction
fi

if [ "$1" = "--help" ] || [ "$1" = "-h" ]
then
   helpFunction
fi
if [ "$2" = "--upload" ] || [ "$2" = "-u" ]
then
  python3 build_package.py -i $1 --upload 'true'
else
 python3 build_package.py -i $1
fi
