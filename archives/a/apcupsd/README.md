# apcupsd

APC UPS power management daemon for controlling APC UPS systems.

## Description
apcupsd is a daemon for controlling APC UPS systems. It can monitor UPS status,
perform shutdowns during power failures, and provide network monitoring capabilities.

## OpenHarmony Notes
- pthread_cancel is not supported on OpenHarmony (musl libc)
- shutdown/wall commands are not available, dummy commands created
- HMDFS umask restrictions require configure modification

## Version History
- 3.14.14: Built successfully (2026-06-03)
