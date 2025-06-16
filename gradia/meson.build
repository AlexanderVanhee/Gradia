# Install gradient library
shared_library(
  'gradient_gen',
  'graphics/gradient_gen.c',
  install: true,
  install_dir: MODULE_DIR,
  install_rpath: '$ORIGIN',
  link_args: ['-lm'],
)

# Generate Python executable
configure_file(
  input: 'gradia.in',
  output: 'gradia',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'r-xr-xr-x'
)

# Generate constants module
configure_file(
  input: 'constants.in',
  output: 'constants.py',
  configuration: conf,
  install: true,
  install_dir: MODULE_DIR
)

# Root sources
gradia_sources = [
  '__init__.py',
  'main.py',
  'clipboard.py',
  'app_constants.py',
]

# Install sources
install_data(gradia_sources, install_dir: MODULE_DIR)

# Install backend modules
install_subdir('backend', install_dir: MODULE_DIR)

# Install graphics modules
install_subdir('graphics', install_dir: MODULE_DIR)

# Install overlay modules
install_subdir('overlay', install_dir: MODULE_DIR)

# Install ui modules
install_subdir('ui', install_dir: MODULE_DIR)

# Install utils modules
install_subdir('utils', install_dir: MODULE_DIR)
