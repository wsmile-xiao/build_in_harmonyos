project('test_tls_backend', 'c', default_options: ['c_std=c11'])

glib_dep = dependency('glib-2.0')
gio_dep = dependency('gio-2.0')

executable(
  'test_tls_backend',
  'test_tls_backend.c',
  dependencies: [glib_dep, gio_dep],
)