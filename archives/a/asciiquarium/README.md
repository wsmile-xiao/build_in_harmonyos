# Asciiquarium

Asciiquarium is an aquarium/sea animation in ASCII art.  
Enjoy the mysteries of the sea from the safety of your own terminal!

Original Author: Kirk Baucom <kbaucom@schizoid.com>

## Dependencies

- Perl 5.42.0+
- Curses Perl module
- Term::Animation Perl module

## Installation

1. Install Perl dependencies:
   - `cpan install Curses`
   - `cpan install Term::Animation`

2. Copy `asciiquarium` to `/usr/local/bin` or `/usr/local/games`

## Usage

```
asciiquarium [options]
Options:
  -c --classic      Only show species from Asciiquarium 1.0
  -t --transparent  Transparent background
  -s --screensaver  Exit on any keypress
  -v --version      Print version and exit

Hotkeys:
  q - quit
  r - redraw  
  p - pause
  t - toggle transparency
```
