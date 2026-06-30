# libbson

libbson is a BSON serialization library, part of the mongo-c-driver project.
It provides utilities for creating, parsing, and manipulating BSON documents.

## Available Versions

- **1.27.1** (published): Built from Savannah release tarball with cmake

## Build Notes

- Build system: cmake
- Savannah release tarballs include generated cmake modules (build/cmake/)
- GitHub archive tarballs lack these modules, requiring custom stubs
- Must use Mode B (manual cmake/make) to avoid .work directory re-initialization clearing cmake modules

## Quality Status

- Quality gates G1-G4: ✅ PASS
- Functional test: ✅ 52/52 pass (2026-06-01)
- Pre-compiled package: ✅ Ready for upload
