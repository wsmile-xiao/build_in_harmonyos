# jbigkit

JBIG1 (JBIG-KIT) compression library and tools for bi-level image encoding/decoding, implementing the ITU-T T.82 (JBIG1) and T.85 (JBIG1 progressive) standards.

## Version 2.1

- **Status**: published
- **Build date**: 2026-06-13
- **Build system**: makefile (simple Makefile, no autotools)
- **Compiler**: clang 15.0.4

### Products

- `bin/pbmtojbg` — PBM to JBIG converter (JBIG1)
- `bin/jbgtopbm` — JBIG to PBM converter (JBIG1)
- `bin/pbmtojbg85` — PBM to JBIG converter (T.85)
- `bin/jbgtopbm85` — JBIG to PBM converter (T.85)
- `lib/libjbig.a` — JBIG1 static library
- `lib/libjbig85.a` — T.85 static library
- `include/jbig.h` — JBIG1 API header
- `include/jbig85.h` — T.85 API header
- `include/jbig_ar.h` — Arithmetic coding header

### Dependencies

None (standalone library).
