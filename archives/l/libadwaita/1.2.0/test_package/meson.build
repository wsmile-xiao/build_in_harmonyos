project('libadwaita-test', 'c',
  version: '1.0',
  default_options: ['warning_level=2'])

adw_dep = dependency('libadwaita-1')

test_libadwaita = executable('test_libadwaita',
  sources: ['test.c'],
  dependencies: [adw_dep],
  install: false)

test('test_libadwaita', test_libadwaita)
