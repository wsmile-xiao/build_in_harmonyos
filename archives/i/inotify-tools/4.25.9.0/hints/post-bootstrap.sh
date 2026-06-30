#!/bin/bash
# Post-bootstrap hook for inotify-tools
# Fix HMDFS compatibility: remove umask 077 from configure
# HMDFS doesn't allow creating temp directories with umask 077
# This is a known OHOS platform issue (ref: E046-like, shc build experience)
set -e
sed -i 's/umask 077 && mktemp/umask 002 \&\& mktemp/g' configure
sed -i 's/umask 077 && mkdir/umask 002 \&\& mkdir/g' configure