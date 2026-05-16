#!/bin/bash
# cmake configure wrapper for libusrsctp
# This file is used by clean-verify G0 process

cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
      -Dsctp_build_programs=OFF \
      -B build \
      .

# cmake projects don't have separate configure step
# return success to continue build
exit 0