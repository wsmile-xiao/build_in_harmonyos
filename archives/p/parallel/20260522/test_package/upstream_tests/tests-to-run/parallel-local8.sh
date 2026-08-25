#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

par_dummy() { true; }

export -f $(compgen -A function | grep par_)
compgen -A function | grep par_ | sort |
    parallel -j0 --tag -k --joblog +/tmp/jl-`basename $0` '{} 2>&1'
