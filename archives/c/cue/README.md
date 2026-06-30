# cue - Configuration Language

## Overview

CUE (Configuration Unification Engine) is an open-source data validation language created by Google. It is a superset of JSON with powerful schema validation, data templating, and constraint features.

## Key Features

- Type checking and validation for configuration data
- Schema definition and enforcement
- Data templating with constraints
- JSON superset - valid JSON is valid CUE
- Go-based implementation

## Version Information

- Current version: 0.11.2
- Written in Go
- CGO_ENABLED=0 static binary for OpenHarmony

## Build Notes

For Go 1.26 compatibility, a patch is needed for the vendored `golang.org/x/tools/tokeninternal` module. See `0.11.2/patches/` for details.