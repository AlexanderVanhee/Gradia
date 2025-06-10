pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
python = import('python')
py_installation = python.find_installation('python3')
moduledir = get_option('prefix') / get_option('libdir') / 'python3.12' / 'site-packages' / 'gradia'

gnome = import('gnome')
gnome.compile_resources('gradia',
  'gradia.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

gradient_lib = shared_library(
  'gradient_gen',
  'graphics/gradient_gen.c',
  install: true,
  install_dir: moduledir,
  install_rpath: '$ORIGIN',
  link_args: ['-lm'],
)

conf = configuration_data()
conf.set('PYTHON', py_installation.full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'gradia.in',
  output: 'gradia',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'r-xr-xr-x'
)

gradia_sources = [
  '__init__.py',
  'main.py',
  'clipboard.py',
  'constants.py'
]

install_data(gradia_sources, install_dir: moduledir)
install_subdir('graphics', install_dir: moduledir)
install_subdir('ui', install_dir: moduledir)
install_subdir('backend', install_dir: moduledir)
install_subdir('overlay', install_dir: moduledir)