#!/bin/bash

# SPDX-FileCopyrightText: 2007-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
# SPDX-License-Identifier: GPL-3.0-or-later

cd $(dirname $0)
vagrantid=$(pwd | perl -pe 's:.*/([^/]+/[^/]+):$1:')
echo $vagrantid
if vagrant box list | grep $vagrantid ; then
    : skip
else
    url=$(curl -s https://vagrantcloud.com/api/v2/vagrant/$vagrantid | jq -r '[.versions[] | select(.providers[].name=="virtualbox")] | max_by(.version) .providers[] | select(.name=="virtualbox") .url')
    echo "$url"
    wget -N $url
    vagrant box add --name $vagrantid vagrant.box
    vagrant box list
fi

