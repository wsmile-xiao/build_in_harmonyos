# sinntp

sinntp is a tiny non-interactive NNTP client for pulling, pushing, fetching and listing Usenet newsgroups.

## Features

- \`sinntp pull\`: fetch new articles of given groups into mbox files (with43 last-fetched tracking).
- \`sinntp push\`: send local articles to the NNTP server.
- \`sinntp get\`: download individual messages in RFC822 format.
- \`sinntp list\`: list available newsgroups.
- Convenience wrappers \`nntp-get\` / \`nntp-list\` / \`nntp-pull\` / \`nntp-push\` (POSIX sh one-liners).
- Plugin pipeline (\`mimify\`, \`strip_headers\`, \`debug\`) for pulled/pushed messages.

## OHOS adaptation

- Pure Python package (stdlib only: nntplib, argparse, mailbox, email); no C compilation and no third-party runtime dependencies.
- Installed payload: entry scripts \`sinntp\` + \`nntp-*\` to \`bin/\` (chmod 755), \`plugins.py\`/\`utils.py\` to both \`bin/\` (so script-local \`import utils\` keeps working) and \`lib/python/site-packages\` (consumer \`import utils\`).
- Entry scripts run with \`python3 <script> --help\`; the \`nntp-*\` wrappers are \`#!/bin/sh\` one-liners delegating to \`sinntp\`, invoke them via \`sh\` on systems without \`/bin/sh\`.
- Upstream suite \`tests.py\` (14 unittest methods) runs in \`build()\` via \`python3 tests.py -v\`; no network access is needed (pure parsing/XDG/join-lines unit tests).
- XDG data dir follows the spec: invalid/relative \`XDG_DATA_HOME\` falls back to \`~/.local/share\`.

## Dependencies

- Build: none (script install).
- Runtime: python3 (stdlib only).

## References

- Homepage: https://jwilk.net/software/sinntp
- Source: https://github.com/jwilk/sinntp
- Release 1.6 tarball: https://github.com/jwilk/sinntp/releases/download/1.6/sinntp-1.6.tar.gz
