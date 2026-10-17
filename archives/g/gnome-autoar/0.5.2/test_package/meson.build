project(
  'test_gnome_autoar',
  'c',
  default_options: ['c_std=c99', 'warning_level=2'],
)

gnome_autoar = dependency('gnome-autoar-0', required: true)

executable(
  'test_gnome_autoar',
  'test.c',
  dependencies: gnome_autoar,
  install: true,
  install_dir: 'bin',
  install_rpath: '$ORIGIN/../lib',
)
