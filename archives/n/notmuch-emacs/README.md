# notmuch-emacs

`notmuch-emacs` packages the Emacs Lisp front-end shipped in the official
Notmuch release tarball. It provides the Lisp features needed by packages such
as `ol-notmuch`.

This archive intentionally does not build or install the native Notmuch CLI,
library, or mail database tooling. Runtime mail operations still require a
matching Notmuch program outside this pure Emacs Lisp package.
