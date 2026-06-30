#!/bin/bash
# Hints for howard-hinnant-date 3.0.4 cmake configuration
# This file helps the clean-verify script configure the project correctly

# cmake configure options (required for this project)
CMAKE_OPTIONS="-DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_TZ_LIB=ON -DMANUAL_TZ_DB=ON"

# Platform note: toybox sh has issues with cmake subprocess; use bash if available
# This is a header-only + static library, no binary executables to verify