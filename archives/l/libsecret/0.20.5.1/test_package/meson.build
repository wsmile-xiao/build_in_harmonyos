project('test_libsecret', 'c')

dep = dependency('libsecret-1', method: 'pkg-config')
libdir = dep.get_variable(pkgconfig: 'libdir')
# libsecret-1.so pulls in glib/gcrypt at load time; their libdirs must be on
# the RPATH too or the loader rejects the whole chain.
glib_libdir = dependency('glib-2.0', method: 'pkg-config').get_variable(pkgconfig: 'libdir')
gcrypt_libdir = dependency('libgcrypt', method: 'pkg-config').get_variable(pkgconfig: 'libdir')

# ---------------------------------------------------------------------------
# 1) link_probe — proves the exported `secret-1` pkg-config module yields
#    usable Cflags (public headers) and Libs (-lsecret-1), i.e. the downstream
#    link contract. Run by the test driver with the produced .so copies.
# ---------------------------------------------------------------------------
link_probe = executable('link_probe', 'link_probe.c',
  dependencies: dep,
  # $ORIGIN first — the OHOS loader fails on symlinked libs in the Conan cache,
  # so the real copies beside the binary must win. build_rpath is applied by the
  # linker itself, so the signature stays valid. The probes are deliberately NOT
  # meson-installed: install-time RPATH rewriting would strip the signature
  # (E077) and make the harness un-runnable.
  build_rpath: '$ORIGIN:' + libdir + ':' + glib_libdir + ':' + gcrypt_libdir,
)

# ---------------------------------------------------------------------------
# 2) dlopen_probe — the acceptance test. NOT linked against libsecret, so
#    dlopen(RTLD_NOW) of the produced libsecret-1.so.0 really has to map and
#    relocate the artifact (an unsigned/stale `.codesign` makes it fail with
#    EACCES, which is the published 0.20.5 defect).
# ---------------------------------------------------------------------------
cc = meson.get_compiler('c')
dl_dep = cc.find_library('dl', required: false)
dlopen_probe = executable('dlopen_probe', 'test.c',
  dependencies: dl_dep,
)

test('link_probe', link_probe)
test('dlopen_probe', dlopen_probe)
