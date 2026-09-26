# wtmpdb

`wtmpdb` records logins/logouts in an SQLite database instead of the
classic utmp/wtmp files, providing `wtmpdb` CLI, `libwtmpdb`, and the
`pam_wtmpdb` PAM module. On HarmonyOS PC the wtmpdbd daemon (systemd +
varlink) is not delivered; see the version notes.

## Versions

| Version | Status |
| --- | --- |
| 0.75.0 | built |

Homepage: https://github.com/thkukuk/wtmpdb
