project('epoxy-test', 'c',
  version: '1.0.0',
  default_options: ['warning_level=2'])

epoxy_dep = dependency('epoxy', required: true)

epoxy_test = executable('epoxy-test',
  'test_epoxy.c',
  dependencies: [epoxy_dep],
  install: false)

test('epoxy-test', epoxy_test)
