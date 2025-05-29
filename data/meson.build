desktop_file = i18n.merge_file(
        input: 'be.alexandervanhee.gradia.desktop.in',
       output: 'be.alexandervanhee.gradia.desktop',
         type: 'desktop',
       po_dir: '../po',
      install: true,
  install_dir: get_option('datadir') / 'applications'
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils, args: [desktop_file])
endif

appstream_file = i18n.merge_file(
        input: 'be.alexandervanhee.gradia.metainfo.xml.in',
       output: 'be.alexandervanhee.gradia.metainfo.xml',
       po_dir: '../po',
      install: true,
  install_dir: get_option('datadir') / 'metainfo'
)

appstreamcli = find_program('appstreamcli', required: false, disabler: true)
test('Validate appstream file', appstreamcli,
     args: ['validate', '--no-net', '--explain', appstream_file])

install_data('be.alexandervanhee.gradia.gschema.xml',
  install_dir: get_option('datadir') / 'glib-2.0' / 'schemas'
)

install_data([
  'fonts/Caveat-VariableFont_wght.ttf',
  'fonts/LICENSE-OFL.txt',
],
install_dir: join_paths(get_option('datadir'), 'fonts')
)

compile_schemas = find_program('glib-compile-schemas', required: false, disabler: true)
test('Validate schema file',
     compile_schemas,
     args: ['--strict', '--dry-run', meson.current_source_dir()])


service_conf = configuration_data()
service_conf.set('bindir', get_option('prefix') / get_option('bindir'))
configure_file(
  input: 'be.alexandervanhee.gradia.service.in',
  output: 'be.alexandervanhee.gradia.service',
  configuration: service_conf,
  install_dir: get_option('datadir') / 'dbus-1' / 'services'
)

gnome = import('gnome')
resources = gnome.compile_resources(
  'resources',
  'resources.data.gresource.xml.in',
  gresource_bundle: true,
  source_dir: meson.current_build_dir(),
  install: true,
  install_dir: get_option('datadir') / meson.project_name(),
)

subdir('icons')
