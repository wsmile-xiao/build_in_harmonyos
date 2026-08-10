# dgit

Integration between git and Debian-style archives.

## Overview

dgit (with the associated infrastructure) makes it possible to treat the Debian archive as a git repository:

- **dgit push** constructs uploads from git commits
- **dgit clone** and **dgit fetch** construct git commits from uploads

## Key Features

- Treat Debian archive as a git repository
- Bidirectional synchronization between git and Debian packages
- Support for NMU (Non-Maintainer Upload) workflow
- Integration with git-buildpackage and other Debian packaging tools

## Links

- **Upstream**: https://salsa.debian.org/dgit-team/dgit
- **Browsable Repository**: https://browse.dgit.debian.org/dgit.git/
- **Debian Package**: https://packages.debian.org/sid/dgit
