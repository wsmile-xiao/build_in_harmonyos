#!/bin/sh
set -eu
reop="$1"
work="$2"
cd "$work"
printf 'HarmonyOS reop consumer test\n' > message.txt
"$reop" -G -p public -s secret -n
"$reop" -S -s secret -m message.txt
"$reop" -Vq -p public -m message.txt -x message.txt.sig
"$reop" -E -p public -s secret -m message.txt
"$reop" -D -p public -s secret -x message.txt.enc -m restored.txt
cmp message.txt restored.txt
echo 'Consumer sign, verify, encrypt, decrypt: passed'
