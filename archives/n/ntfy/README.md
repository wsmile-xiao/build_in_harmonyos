# ntfy

## Description

ntfy is a simple HTTP-based push notification service. It allows you to send notifications to your phone or desktop via scripts from any computer, entirely without signup, cost, or setup.

- **Homepage**: https://ntfy.sh/
- **Source**: https://github.com/binwiederhier/ntfy

## Available Versions

| Version | Status | Notes |
|---------|--------|-------|
| 2.15.0-r5 | published | Go build with CGO (sqlite3 support) |

## Build System

- Go (CGO_ENABLED=1 for mattn/go-sqlite3)
- Build tags: sqlite_omit_load_extension, osusergo, netgo