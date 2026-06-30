# spglib

C library for finding and handling crystal symmetries.

## Homepage

https://spglib.readthedocs.io/en/latest/

## License

BSD-3-Clause

## Description

Spglib is a C library for finding and handling crystal symmetries. It provides functions to:
- Find space group symmetries
- Get standardized unit cells
- Find primitive cells
- Calculate k-point grids
- Handle magnetic symmetries

## Available Versions

| Version | Status | Date |
|---------|--------|------|
| 2.7.0 | published | 2026-06-12 |

## Dependencies

None (pure C library with no required dependencies).

## Usage

```c
#include <spglib.h>

// Get dataset for a crystal structure
SpglibDataset* dataset = spg_get_dataset(lattice, position, types, num_atom, symprec);
printf("Space group: %d (%s)\n", dataset->spacegroup_number, dataset->international_symbol);
spg_free_dataset(dataset);
```

### pkg-config

```bash
export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
pkg-config --cflags --libs spglib
```