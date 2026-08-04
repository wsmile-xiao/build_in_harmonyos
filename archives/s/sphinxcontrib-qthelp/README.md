# sphinxcontrib-qthelp

`sphinxcontrib-qthelp` is the Sphinx builder extension that generates Qt Help
project (`.qhp`) and collection project (`.qhcp`) files.

## Features

- Generate Qt Help project metadata from a Sphinx document tree.
- Emit table-of-contents, keyword, namespace, and collection information.
- Escape document titles and index entries for Qt Help XML.
- Integrate as the Sphinx `qthelp` builder.

## OHOS adaptation

Version 2.0.0 is an OS-independent Python namespace package. The Conan package
installs `sphinxcontrib.qthelp` under `lib/python` and exports that directory
through `PYTHONPATH`. No source patch or native compilation is required.

Sphinx is intentionally not a Conan requirement: Sphinx itself distributes and
loads this extension, so a reverse dependency would be circular. A consumer
must provide a compatible Sphinx installation.

## Dependencies

- Runtime consumer: Sphinx 5 or newer.
- Upstream tests: Sphinx 9.1.0, pytest 9.1.1, defusedxml 0.7.1.
- Native libraries: none.

## References

- Source: https://github.com/sphinx-doc/sphinxcontrib-qthelp/
- Package: https://pypi.org/project/sphinxcontrib-qthelp/2.0.0/
