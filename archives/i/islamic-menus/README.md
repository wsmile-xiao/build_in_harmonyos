# Islamic Menus

islamic-menus provides XDG menu categories, localized desktop-directory entries and SVG category icons for Islamic applications.

## Function Overview

- Supplies generic and GNOME merged-menu fragments.
- Defines Islamic Software and Quran desktop-directory entries with gettext translations.
- Provides the category SVG icons referenced by those entries.

## HarmonyOS Adaptation

- This is a data-only package; it does not install a GUI or standalone executable.
- Conan installs menu fragments under `etc/xdg/menus/`, directory entries under `share/desktop-directories/`, and icons under `share/icons/hicolor/scalable/categories/`.
- Conan runtime environment adds the package's `etc/xdg` and `share` directories to `XDG_CONFIG_DIRS` and `XDG_DATA_DIRS`.
- A desktop needs an XDG-aware consumer to display these menus; the package alone does not add menus to the HarmonyOS desktop shell.

## Dependencies

- Build dependency: `intltool/0.51.0` for generating translated `.directory` files.
- Runtime Conan dependencies: none.

## References

- Upstream project: https://launchpad.net/islamic-menus
- Source archive: https://deb.debian.org/debian/pool/main/i/islamic-menus/islamic-menus_1.0.5.orig.tar.bz2
