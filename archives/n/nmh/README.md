# nmh

Classic Unix command-line mail user agent (MUA).  nmh provides a
family of small interoperating commands to read (inc, scan, show),
compose (comp, forw, repl), organise (folder, refile, rmm, packf,
sortm) and send (send, post, sendfiles, whatnow, whom) mail.

This adaptation builds nmh 1.8 for HarmonyOS PC (aarch64) with the
autotools build system and installs:

- `bin/` - 46 command entry points (including the flist/folder/new/show
  aliases flists, folders, fnext, fprev, next, prev, unseen)
- `libexec/nmh/` - 14 helper programs (ap, dp, fmtdump, mhl, mkstemp,
  post, rcvdist, rcvpack, rcvstore, rcvtty, slocal, spost, viamail)
- `etc/nmh/` - example profiles and mail transport configuration
- `share/` - man pages and documentation

See `1.8/` for the current recipe.

## Files

- `README.md` - this file
- `manifest.yaml` - software level metadata
- `commands.json` - command line tool declaration
- `1.8/` - recipe for nmh 1.8
