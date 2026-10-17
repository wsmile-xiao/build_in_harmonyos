project('test_libsecret', 'c')

dep = dependency('libsecret-1', method: 'pkg-config')
libdir = dep.get_variable(pkgconfig: 'libdir')
# libsecret-1.so pulls in glib/gcrypt at load time; their libdirs must be
# on the RPATH too or the loader rejects the whole chain.
glib_libdir = dependency('glib-2.0', method: 'pkg-config').get_variable(pkgconfig: 'libdir')
gcrypt_libdir = dependency('libgcrypt', method: 'pkg-config').get_variable(pkgconfig: 'libdir')

exe = executable('test_libsecret', 'test.c',
  dependencies: dep,
  install: true,
  # RPATH carries the lib search path at runtime (env may not propagate);
  # $ORIGIN first — the loader fails on symlinked libs in the Conan cache,
  # so real copies beside the binary must win.
  build_rpath: '$ORIGIN:' + libdir + ':' + glib_libdir + ':' + gcrypt_libdir,
  install_rpath: '$ORIGIN:' + libdir + ':' + glib_libdir + ':' + gcrypt_libdir,
)

test('test_libsecret', exe)
