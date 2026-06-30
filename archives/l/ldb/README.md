# ldb

## What is it?

ldb is a LDAP-like embedded database library from the Samba project. It provides a hierarchical database API with LDAP-like query syntax, used as a core component in Samba's Active Directory implementation.

## Key Features

- LDAP-like query API for embedded use
- TDB/TDB2 backends for fast local storage
- Module-based architecture (sorting, constraints, etc.)
- Python bindings available (disabled in OHOS build)

## OHOS/HarmonyOS Adaptation

- **Build type**: waf (Samba Python-based build system)
- **4 patches required**:
  - lib/replace/replace.h — musl libc compatibility (#ifdef __OHOS__ guards for mkstemp/strtoull/strtoll)
  - lib/replace/wscript — private_library=False + HAVE_SECURE_MKSTEMP adaptation
  - third_party/cmocka/cmocka.h — uintptr_t typedef conflict with musl
  - wscript — ldb_mdb_int dependency fix
- **configure option**: `--disable-python`
- **Dependencies**: lmdb (system), libiconv (precompiled), openldap (system)

## Version 2.9.2

- Status: published
- Build date: 2026-06-09
- 4 patches applied for musl libc compatibility
- C tests: 56 passed / 2 failed (96.5%)