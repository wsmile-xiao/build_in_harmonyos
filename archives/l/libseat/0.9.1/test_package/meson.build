project(
  'test-libseat',
  'c',
  version: '0.9.1',
  default_options: ['c_std=c11', 'warning_level=2'],
)

cc = meson.get_compiler('c')
libseat = cc.find_library(
  'seat',
  dirs: [get_option('libseat_lib_dir')],
  static: true,
  required: true,
)
libseat_dep = declare_dependency(
  compile_args: ['-I' + get_option('libseat_include_dir')],
  dependencies: [libseat],
)

test_libseat = executable(
  'test_libseat',
  'test_package.c',
  dependencies: [libseat_dep],
  install: false,
)

test('test_libseat', test_libseat)