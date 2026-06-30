# acct — GNU Accounting Utilities

GNU Accounting Utilities provide tools for process and login accounting on Unix-like systems.

## Tools

| Tool | Description |
|------|-------------|
| ac | Prints statistics about users' connect time |
| last | Shows listing of last logged in users |
| lastcomm | Shows listing of last executed commands |
| accton | Turns process accounting on or off |
| dump-utmp | Prints contents of an utmp file in human-readable format |
| dump-acct | Prints contents of an acct file in human-readable format |
| sa | Summarizes information about previously executed commands |

## Versions

| Version | Status | Date |
|---------|--------|------|
| 6.6.4 | published | 2026-06-30 |

## Build

```bash
conan install --requires=acct/6.6.4@ohpcd/stable --build=missing
```

## Homepage

https://www.gnu.org/software/acct/
