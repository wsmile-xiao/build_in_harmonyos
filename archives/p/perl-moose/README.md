# perl-moose

Perl Moose — A postmodern object system for Perl 5.

## Versions

| Version | Status | Date |
|---------|--------|------|
| 2.4000 | built | 2026-06-23 |

## Description

Moose is a complete object system for Perl 5. It provides:
- Classes, attributes, methods
- Roles (similar to mixins/traits)
- Type constraints and coercions
- Method modifiers (before, after, around)
- Immutable classes for performance
- Native traits (Array, Hash, String, etc.)

## OpenHarmony Notes

On OpenHarmony, HMDFS prevents dlopen from loading .so files on `/storage/Users/currentUser/`.
A pure Perl fallback patch is applied to `Class/MOP.pm` to ensure all XS-provided methods
have pure Perl implementations, enabling full Moose functionality without XS acceleration.

XS .so files are compiled and signed, ready for installation to `/data/service/hnp/` (hnp_file:s0 label)
where dlopen works. In that case, XS acceleration will be automatically used.
