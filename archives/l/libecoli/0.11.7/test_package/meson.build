project(
  'test-libecoli',
  'c',
  version: '0.11.7',
  default_options: ['c_std=c99', 'warning_level=2'],
)

cc = meson.get_compiler('c')
ecoli = cc.find_library(
  'ecoli',
  dirs: [get_option('libecoli_lib_dir')],
  static: true,
  required: true,
)
ecoli_dep = declare_dependency(
  compile_args: ['-I' + get_option('libecoli_include_dir')],
  dependencies: [ecoli],
)

test_libecoli = executable(
  'test_libecoli',
  'test_package.c',
  dependencies: [ecoli_dep],
  install: false,
)

test('test_libecoli', test_libecoli)
