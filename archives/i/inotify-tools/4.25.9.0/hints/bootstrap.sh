#!/bin/bash
# Bootstrap script for inotify-tools
# GitHub tag tarballs don't include configure script
# This script runs autoreconf to generate it
set -e
autoreconf -fi