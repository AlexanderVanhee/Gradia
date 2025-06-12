python = import('python')
py_installation = python.find_installation('python3')

gnome = import('gnome')



gnome.compile_resources('gradia',
  'gradia.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: PKGDATA_DIR,
)

gradient_lib = shared_library(
  'gradient_gen',
  'graphics/gradient_gen.c',
  install: true,
  install_dir: MODULE_DIR,
  install_rpath: '$ORIGIN',
  link_args: ['-lm'],
)



configure_file(
  input: 'gradia.in',
  output: 'gradia',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'r-xr-xr-x'
)

configure_file(
  input: 'constants.in',
  output: 'constants.py',
  configuration: conf,
  install: true,
  install_dir: MODULE_DIR
)

gradia_sources = [
  '__init__.py',
  'main.py',
  'clipboard.py',
  'app_constants.py',
]

install_data(gradia_sources, install_dir: MODULE_DIR)
install_subdir('graphics', install_dir: MODULE_DIR)
install_subdir('ui', install_dir: MODULE_DIR)
install_subdir('utils', install_dir: MODULE_DIR)
install_subdir('backend', install_dir: MODULE_DIR)
install_subdir('overlay', install_dir: MODULE_DIR)
