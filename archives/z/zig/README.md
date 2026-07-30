# Zig

Zig is a general-purpose programming language and toolchain for maintaining
robust, optimal, and reusable software.

This archive provides Zig as a Conan build tool package so downstream recipes
can use:

```python
self.tool_requires("zig/0.16.0")
```

The package preserves the official Zig distribution layout inside `bin/`. On
OHOS, `bin/zig` is a small compatibility wrapper, while the signed official
ELF remains available as `bin/zig-real` with its required `lib/` directory as a
sibling. Downstream recipes can still invoke `zig` from PATH.
