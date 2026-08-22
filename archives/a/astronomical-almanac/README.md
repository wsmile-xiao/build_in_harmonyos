# astronomical-almanac

Astronomical Almanac 5.6 — planetary ephemeris and celestial calculations
based on algorithms from "The Astronomical Almanac" (U.S. Naval Observatory).

## Features

- Planetary positions (Mercury through Pluto)
- Solar and lunar ephemeris
- Coordinate transformations (equatorial, ecliptic, horizontal)
- Nutation and precession
- Atmospheric refraction corrections
- Rise/set/transit calculations
- Star position reduction
- Delta T computation

## Source

- Repository: https://github.com/DouglasAllen/clib-astronomical-almanac-5.6
- Author: S. L. Moshier (1987-2006)
- License: Public Domain

## Build

Plain Makefile. Depends only on the system math library (`-lm`).

```
make all CC=clang
make install PREFIX=/usr/local DESTDIR=<destdir>
```

## Usage

- `aa` — Interactive astronomical almanac calculator
- `conjunct` — Planetary conjunction calculator
- `moonrise` — Moonrise/moonset calculator
