#!/bin/sh
# R34: Execute the aseqjoy binary to verify the package works.
aseqjoy -h 2>&1 | grep -F 'aseqjoy version 0.0.2'
