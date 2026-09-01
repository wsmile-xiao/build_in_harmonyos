# RDKit

RDKit is a collection of cheminformatics and machine learning tools written in C++ and Python.

## Overview

The RDKit library provides core cheminformatics functionality including:
- Molecule parsing and manipulation (SMILES, SMARTS, MOL, SDF, InChI)
- Substructure searching
- Molecular fingerprints
- 2D coordinate generation and depiction
- 3D descriptors and shape analysis
- Molecular property prediction

## Package Information

- **Upstream**: https://github.com/rdkit/rdkit
- **License**: BSD-3-Clause
- **Build system**: CMake
- **Language**: C++ (with optional Python bindings)

## Dependencies

- boost (serialization, regex, iostreams, system, filesystem, thread)
- eigen (3D descriptors)
- freetype (molecular drawing)
- libpng (image output)
- zlib (compression)
