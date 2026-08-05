# bmake

Portable make implementation derived from NetBSD make.

## Version

- `20200710`: built for OHOS aarch64.

## OHOS Notes

The package provides `bmake` and `bmake-20200710`, together with the required
`share/mk` files. Conan run environments configure `MAKESYSPATH` automatically.

## Verification

```bash
bmake -f Makefile
```

## References

- [Upstream bmake documentation](https://www.crufty.net/help/sjg/bmake.html)
