# ots

Open Text Summarizer — automatic text summarization library and command line tool.

The program reads a text and decides which sentences are important and which
are not. OTS creates a short summary or highlights the main ideas in the text.
It works as both a C library (`libots-1`) and a CLI tool (`ots`), and can
print the summarized text as plain text or highlighted HTML.

## Build Artifacts

- `bin/ots` — text summarization command-line tool
- `lib/libots-1.a` — static summarization library
- `include/libots-1/ots/libots.h` — C API header
- `lib/pkgconfig/libots-1.pc` — pkg-config metadata
- `share/ots/` — stemming dictionaries (`dic/*.xml`)

## Dependencies

- glib/2.84.0.1 (data structures, GOption CLI parsing)
- libxml2/2.15.3 (XML dictionary loading)
- popt/1.16 (legacy option parsing probe)
