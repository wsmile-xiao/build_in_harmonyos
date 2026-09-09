# iso-codes

https://salsa.debian.org/iso-codes-team/iso-codes

This project provides lists of various ISO standards (e.g. country,
language, language scripts, and currency names) in one place, rather
than repeated in many programs throughout the system.

Currently there are lists of languages and countries embedded in
several different programs, which leads to dozens of lists of
200 languages, translated into more than 90 languages ... not
very efficient.

With this project, we create a single "gettext domain" for every
supported ISO standard which contains the translations of
that domain. It is easy for a programmer to re-use those
translations instead of maintaining their own translation
infrastructure. Moreover, the programmer does not need to follow
changes in the ISO standard and will not work with outdated
information.

## Supported ISO Standards

- ISO 639-2 (language codes)
- ISO 639-3 (language codes)
- ISO 639-5 (language family codes)
- ISO 3166-1 (country codes)
- ISO 3166-2 (country subdivision codes)
- ISO 3166-3 (formerly used country codes)
- ISO 4217 (currency codes)
- ISO 15924 (script codes)

## Installation

Data files are installed to:

- JSON files: `/usr/local/share/iso-codes/json/`
- Translation files: `/usr/local/share/{domain}/`
- pkg-config file: `/usr/local/share/pkgconfig/iso-codes.pc`

Version 4.20.1 uses Meson and additionally installs JSON schemas,
generated compatibility XML files, and legacy XML and gettext-domain
symbolic links. The Conan package keeps these architecture-independent
resources below `share/`.
