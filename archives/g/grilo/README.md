# grilo

Grilo is a framework that provides access to different sources of multimedia content, using a pluggable system.

## Description

Grilo is a framework focused on making media discovery and browsing easy for application developers. It provides a simple and flexible API to search, browse, and access multimedia content from various sources.

## Features

- Plugin-based architecture for media sources
- Support for multiple media providers
- GObject-based API
- Optional network support (libsoup)
- Optional playlist support (totem-plparser)

## Dependencies

### Required
- glib-2.0 (>= 2.66)
- gio-2.0
- gmodule-2.0
- gobject-2.0
- libxml-2.0
- meson (>= 0.62.0)

### Optional
- libsoup-2.4 or libsoup-3.0 (for network support)
- totem-plparser (for playlist support)
- gobject-introspection (for language bindings)
- vala (for Vala bindings)

## Version History

- 0.3.19: Current version
