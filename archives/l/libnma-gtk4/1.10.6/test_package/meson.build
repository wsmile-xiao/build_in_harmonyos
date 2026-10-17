project('libnma-gtk4-test', 'c',
  version: '1.0',
  default_options: ['warning_level=2'])

libnma_gtk4_dep = dependency('libnma-gtk4')

executable('test_libnma_gtk4',
  sources: ['test_libnma_gtk4.c'],
  dependencies: [libnma_gtk4_dep],
  install: false)
