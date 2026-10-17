# iselect

iSelect is an interactive line selection tool using a full-screen curses
terminal UI.

## Version

- 1.4.2

## Build notes

The upstream release ships Autoconf inputs but no generated `configure` script.
The Conan recipe builds the upstream sources directly and links against
`ncurses/6.6`.
