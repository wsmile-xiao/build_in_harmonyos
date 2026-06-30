# libgnt

libgnt is a GLib Ncurses Toolkit for creating text-mode graphical user interfaces. It is primarily used by Pidgin's Finch client.

## Description

libgnt provides a collection of widgets for building text-mode applications using ncurses. It includes:
- Boxes, buttons, checkboxes
- Combo boxes, entry fields, file selectors
- Labels, lines, menus, progress bars
- Sliders, text views, trees, windows
- Window manager support

## Dependencies

- GLib (≥2.16.0)
- ncurses (with wide character support, ncursesw)
- libxml2 (≥2.6.0, optional)
- Meson (≥0.37.0)

## Usage

libgnt is primarily used by:
- Finch (Pidgin's text-mode client)
- Other text-mode applications requiring graphical UI elements

## Notes

- The library supports both ncursesw (wide character) and ncurses (fallback)
- Optional libxml2 dependency for XML parsing features
- Includes a window manager system for managing multiple text windows