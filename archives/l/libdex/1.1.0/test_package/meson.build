project(
  'test_libdex',
  'c',
  default_options: ['c_std=gnu11', 'warning_level=2'],
)

libdex = dependency('libdex-1', required: true)

executable(
  'test_libdex',
  'test.c',
  dependencies: libdex,
  install: false,
)
