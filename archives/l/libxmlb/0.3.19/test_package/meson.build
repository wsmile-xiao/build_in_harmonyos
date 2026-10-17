project('test_libxmlb', 'c',
  meson_version : '>=0.60.0',
  default_options : ['c_std=c99'],
)

xmlb = dependency('xmlb')

test_libxmlb = executable(
  'test_libxmlb',
  sources : ['test_libxmlb.c'],
  dependencies : [xmlb],
)
