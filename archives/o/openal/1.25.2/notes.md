# openal 1.25.2

- Builds OpenAL Soft as a static library with its always-available null and
  loopback backends.
- Optional desktop/mobile audio backends, utilities, examples, runtime dynamic
  loading, and bundled data are disabled. NEON is enabled for ARM64 targets;
  x86-specific CPU paths remain disabled.
- Guards the upstream HRTF dependency list so disabling bundled HRTF data does
  not produce an empty CMake `add_dependencies` call.
- Enables the ranges implementation shipped with OHOS libc++15 via
  `_LIBCPP_ENABLE_EXPERIMENTAL` and uses the bundled fmt plus portable
  comparison/error-reporting fallbacks for missing C++20 standard-library APIs.
- Avoids globally pre-including the OHOS compatibility header. Build #12361
  showed that pre-including it before OpenAL's bundled GSL headers can poison
  later includes on the CI worker; the helper is now included explicitly after
  GSL only in files that use `openal_compat`.
- Replaces unsupported C++20 `elements_view`, split views, dependent-type
  shorthand, and structured-binding captures with equivalent constructs
  accepted by the OHOS Clang 15 frontend; the delimited-string helper preserves
  the upstream empty-input behavior by not invoking callbacks for an empty list.
- The upstream release has one compilation-only GTest case. Its body is
  preserved in a dependency-free executable, while a separate consumer opens a
  null device and exercises context, buffer, and source APIs.
- Local preflight verified that all four patches apply in order to a clean
  OpenAL 1.25.2 source tree and that OHOS clang accepts the former CI failure
  point (`common/pffft.cpp`) plus the `openal_compat::views::elements` helper
  without the global preinclude.
- After CI Build #12407 reported patch-apply failures in `0003`/`0004`, the
  portability patches were regenerated with normal unified-diff context and
  revalidated against a clean source tree.
- Official OHOS test and CI results remain pending.
