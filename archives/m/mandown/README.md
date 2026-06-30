# mandown

A man-page inspired Markdown pager written in C.

## What is it

Need to lookup things from README? Or from manual page? Or perhaps just want to install something cool...

## Library dependency

Mandown requires `libncurses(w)`, `libxml2` and `libconfig` as compile-time dependencies.

## Installation

```shell
$ git clone https://github.com/Titor8115/mandown.git
$ cd mandown
$ make install
```

## Usage

```shell
$ mdn sample.md
```

Mouse scrolling is supported! (if your terminal emulator allows)

- Move Up: Up, k
- Move Down: Down, j
- Page Up: Space, PgUp, b
- Page Down: Bksp, PgDn, f
- Show href in hyperlink: Tab + Enter, or double click mouse 1
- Exit: q

To read detailed usage, run `mdn -h`

## Embedding

Mandown can also be embedded in your own applications. To render a Markdown document:

```c
#include "mandown.h"

char *str ="# Heading\n\nThis is some **BOLD** *italic* ***EMPHASIZED*** text.";
render_str(str, "md", "Test Title", NULL);
```

Static and shared libraries are available.

## Source

- GitHub: https://github.com/Titor8115/mandown
- Version: v1.0.5.2