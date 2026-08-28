project('gtk4-test', 'c',
  version: '1.0',
  default_options: ['warning_level=2'])

gtk_dep = dependency('gtk4')

executable('gtk4-test',
  sources: ['main.c'],
  dependencies: [gtk_dep],
  install: false)
