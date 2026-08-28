project('sord_test_package', 'c',
  default_options: ['warning_level=0'])

sord_dep = dependency('sord-0', required: true)

test_sord = executable('test_sord', 'test_sord.c',
  dependencies: sord_dep,
  implicit_include_directories: false)

test('sord_c_api', test_sord, suite: 'unit')
