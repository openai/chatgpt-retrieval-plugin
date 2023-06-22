#!/bin/bash
# Must source this file with `source export_env.sh`
# set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ENV="${DIR}/.env"
ENV=${1:-$ENV}

while read -r line || [[ -n "$line" ]]; do
    if [[ ! $line =~ ^# && -n $line ]]; then
        export $line
    fi
done < $ENV
