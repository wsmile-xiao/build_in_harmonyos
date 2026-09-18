#!/bin/sh
# openssl enc -e -aes-256-cbc -md sha256 -in message.txt -out encrypted2.dat -k Martin
# Ported from upstream tests/crack-encrypted2.sh (glv2/bruteforce-salted-openssl 1.5.0).
# Only adaptation: binary resolved from PATH (conanrun) instead of ../.

set -e
BRUTEFORCE_SALTED_OPENSSL=bruteforce-salted-openssl

echo "Bruteforce AES-256-CBC with SHA256"
PASSWORD=$(${BRUTEFORCE_SALTED_OPENSSL} -1 -t 4 -f "dict.txt" \
                                        -d "sha256" encrypted2.dat \
               | grep "Password candidate" \
               | cut -b 21-)

if [ "${PASSWORD}" = "Martin" ];
then
    echo "SUCCESS (Password: ${PASSWORD})"
    exit 0
else
    echo "FAILURE"
    exit 1
fi
