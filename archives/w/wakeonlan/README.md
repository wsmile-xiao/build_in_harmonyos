# wakeonlan

Send "magic packets" to wake up network devices that support Wake-on-LAN.

## Overview

- **Version**: 0.42
- **License**: Artistic-1.0-Perl
- **Source**: https://github.com/jpoliv/wakeonlan
- **Category**: network utility
- **Build system**: Perl (ExtUtils::MakeMaker)

## Description

wakeonlan is a Perl script that sends "magic packets" to Wake-on-LAN capable
network devices, allowing you to remotely power on machines.

## Dependencies

- Perl 5.42+

## Build Notes

- Pure Perl script tool, no compilation needed
- Uses `perl Makefile.PL` + `make` + `make install` workflow
- Shebang needs adaptation for HarmonyOS platform
