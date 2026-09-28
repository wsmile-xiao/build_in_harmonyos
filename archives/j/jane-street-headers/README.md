# jane-street-headers

C header files shared between the various Jane Street OCaml packages.

## Packaged Content

The package installs the complete upstream `include/` directory (5 headers).
It does not build the OCaml/dune toolchain: three of the headers
(`ocaml_utils.h`, `ocaml_utils_macros.h`, `unix_utils.h`) are OCaml binding
templates that require the OCaml runtime `caml/*` headers. The self-contained
headers (`core_params.h`, `jane_common.h`) can be consumed directly on OHOS;
the OCaml-dependent ones remain packaged for source inspection and
OCaml-targeted builds.

## Conan

```cmake
find_package(jane-street-headers CONFIG REQUIRED)
target_link_libraries(app PRIVATE jane-street-headers::jane-street-headers)
```

## References

- [Upstream repository](https://github.com/janestreet/jane-street-headers)
