project('test_jsonrpc_glib', 'c',
  meson_version: '>= 0.49.2',
  default_options: ['buildtype=release'],
)

jsonrpc_dep = dependency('jsonrpc-glib-1.0')

test_exe = executable('test_jsonrpc_glib', 'test.c',
  dependencies: jsonrpc_dep,
)

test('jsonrpc_glib_test', test_exe)
