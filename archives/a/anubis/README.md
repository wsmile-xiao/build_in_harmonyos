# GNU Anubis

GNU Anubis is an SMTP message submission daemon that applies configurable
message transformations between a mail user agent and a mail transport agent.

This archive contains the HarmonyOS PC adaptation of upstream version 4.3.
The Conan package is an application package and installs the `anubis` daemon
under `bin/`. Optional GPGME, GnuTLS, Guile, GSASL, SQL, PCRE, PAM, SOCKS,
and TCP-wrapper integrations are disabled because the core package does not
need those dependencies.

Upstream: https://www.gnu.org/software/anubis/
