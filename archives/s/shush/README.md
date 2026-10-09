# shush

Runs a command (typically a cron job), analyses its output with POSIX or
PCRE2 regular expressions and optionally reports it by mail through a
sendmail(1) compatible program.

- Upstream: https://web.taranis.org/shush/
- Version: 1.2.3
- Current package: `archives/s/shush/1.2.3`
- Supported OpenHarmony architecture: armv8
- HarmonyOS PC notes: there is no MTA and no cron; set the `sendmail`
  configuration parameter or `SHUSH_SENDMAIL`, and set `TMPDIR`
  (`/tmp` is read-only). `-i`/`-u`/`-r` (crontab management) are unavailable.
- Built with `--enable-relaxed-ownership`: HMDFS projects file ownership onto a
  shared identity and forces the group write bit, so configuration files are
  accepted regardless of owner and group write; world writable ones are still
  refused.
