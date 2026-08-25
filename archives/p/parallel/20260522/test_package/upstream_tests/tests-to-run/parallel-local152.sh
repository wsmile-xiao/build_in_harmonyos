#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

echo "### test global config - must run alone so the global config does not confuse others"
echo "### test --tollef in global config"
  echo /etc/parallel/config | sudo parallel "mkdir -p /etc/parallel; echo --tollef > "
  stdout parallel -k echo -- 1 2 3 ::: a b c
  stdout parallel -k --gnu echo ::: 1 2 3 -- a b c
echo "### test --gnu in global config"
  echo --gnu > ~/.parallel/config
  stdout parallel -k echo ::: 1 2 3 -- a b c
  stdout parallel -k --gnu echo ::: 1 2 3 -- a b c
  sudo rm /etc/parallel/config
  rm ~/.parallel/config
echo "<<< End test global config - must run alone so the global config does not confuse others"
