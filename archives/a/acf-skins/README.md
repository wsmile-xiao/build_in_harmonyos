# acf-skins

Theme resources for the Alpine Configuration Framework (ACF) web interface.

The Conan package installs the upstream `alps`, `clouds`, `ice`, `snow`,
`static`, and `wik` assets below `share/acf/www/skins` and exposes that
directory through `cpp_info.resdirs` and the `ACF_SKINS_ROOT` run environment
variable.

This is a platform-independent resource package with no build or runtime
dependencies.
