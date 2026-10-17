# quadrule

QUADRULE is a C library of quadrature rules and numerical integration
routines by John Burkardt.

## Features

- Gaussian quadrature rules including Legendre, Hermite, and Laguerre.
- Clenshaw-Curtis and Newton-Cotes families.
- Rule scaling, exact moments, and weighted summation helpers.

## HarmonyOS adaptation

The bundled GNU configuration scripts recognize the HarmonyOS target triplet,
and the legacy glibc-only `gamma()` call is replaced with standard C99
`tgamma()`. The Conan package supports static and shared builds on AArch64.

## Dependencies

The library uses only the C runtime and the system math library.

## References

- [Upstream project page](https://people.math.sc.edu/Burkardt/c_src/quadrule/quadrule.html)
- [Authoritative snapshot repository](https://salsa.debian.org/science-team/quadrule)
