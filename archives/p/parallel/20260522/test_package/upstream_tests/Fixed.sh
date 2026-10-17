#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

ls tests-to-run/test*.sh | perl -pe 's:(.*/(.*)).sh:cp actual-results/$2 wanted-results/$2:' | sh -x
