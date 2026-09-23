# Draft: libfirm 1.22.0 — aarch64 long double is IEEE quad (LDBL_MANT_DIG==113)

> Source event: `libfirm/1.22.0` HarmonyOS PC (aarch64-linux-ohos) adaptation, executor pc2-39.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

Building libfirm 1.22.0 for aarch64 fails in the tarval float calculator:

```text
ir/tv/fltcalc.c:1079:2: error: "Unsupported long double format"
#error "Unsupported long double format"
```

The upstream code only handles two long-double formats:

```c
#if LDBL_MANT_DIG == 64          /* x87 80-bit extended */
#elif LDBL_MANT_DIG == 53        /* double */
#else
#error "Unsupported long double format"
#endif
```

## Root cause

On aarch64 (and HarmonyOS PC aarch64) `long double` is IEEE 754 **binary128
(quad)**: `LDBL_MANT_DIG == 113`, `sizeof(long double) == 16`, exponent field
15 bits. The upstream preprocessor branches cover only 64 and 53, so the
`#error` fires on aarch64. Measured on this host with clang 15:

```text
LDBL_MANT_DIG=113 sizeof(long double)=16 LDBL_MAX_EXP=16384
```

## Recommended fix

Add the quad branch with the correct IEEE754 descriptor (exponent 15,
mantissa 112, implicit leading one):

```c
#elif LDBL_MANT_DIG == 113
	assert(sizeof(long double) == 16);
	long_double_desc = (float_descriptor_t) { 15, 112, 0 };
```

Keep the 64/53 branches untouched for x86/x86-64 hosts.

## Evidence from libfirm

| Step | Result |
|------|--------|
| before patch | `#error "Unsupported long double format"` at fltcalc.c |
| after patch | fltcalc.o compiled; full `make` exit 0; upstream `make test` 11/11 passed |

## Applicability boundary

- Any C library that builds its own IEEE754 float descriptors or probes
  `LDBL_MANT_DIG` with a hard `#error` fallback.
- Only affects aarch64 (and other quad-long-double targets); x86 builds still
  take the 64 branch.

## Counter-examples / limits

- Do NOT demote `long double` to `double` via compiler flags — this changes
  numeric semantics and can alter the published ABI.
- Do NOT remove the `#error` — an unknown format must still fail loudly.

## Related knowledge

- similar_to: E388 (Boost.Math long-double behavior on OHOS aarch64 — runtime
  numerical behavior, not compile-time format detection).