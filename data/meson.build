gnome = import('gnome')

subdir('ui')

# Translate and install desktop file
desktop_file = i18n.merge_file(
  input: configure_file(
    input: '@0@.desktop.in.in'.format(PROJECT_RDNN_NAME),
    output: '@BASENAME@',
    configuration: conf
  ),
  output: '@0@.desktop'.format(APPLICATION_ID),
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)

# .desktop validation
desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils,
    args: [desktop_file.full_path()],
    depends: desktop_file
  )
endif

# Compile resources
gnome.compile_resources('gradia',
  'gradia.gresource.xml.in',
  gresource_bundle: true,
  dependencies: blueprints,
  source_dir: meson.current_build_dir(),
  install: true,
  install_dir: PKGDATA_DIR
)

# Translate and install Appstream file
metainfo_file = i18n.merge_file(
  input: configure_file(
    input: '@0@.metainfo.xml.in.in'.format(PROJECT_RDNN_NAME),
    output: '@BASENAME@',
    configuration: configuration_data({
      'APP_ID': APPLICATION_ID,
      'PROJECT_URL': PROJECT_URL,
      'VCS_URL': VCS_URL,
      'BUGTRACKER_URL': BUGTRACKER_URL,
      'HELP_URL': HELP_URL,
    })
  ),
  output: '@0@.metainfo.xml'.format(APPLICATION_ID),
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'metainfo')
)

# Appstream validation
appstream_cli = find_program('appstreamcli', required: false)
if appstream_cli.found()
  test('Validate appstream file', appstream_cli,
    args: ['validate', '--no-net', '--explain', metainfo_file.full_path()],
    depends: metainfo_file
  )
endif

# Install fonts
install_data(
  [ 'fonts/Caveat-VariableFont_wght.ttf', 'fonts/LICENSE-OFL.txt' ],
  install_dir: join_paths(get_option('datadir'), 'fonts')
)

# Install GSettings schema
configure_file(
  input: '@0@.gschema.xml'.format(PROJECT_RDNN_NAME),
  output: '@0@.gschema.xml'.format(APPLICATION_ID),
  configuration: conf,
  install: true,
  install_dir: join_paths(get_option('datadir'), 'glib-2.0/schemas')
)

# GSettings schema validation
compile_schemas = find_program('glib-compile-schemas', required: false, disabler: true)
if compile_schemas.found()
  test('Validate schema file', compile_schemas,
    args: ['--strict', '--dry-run', meson.current_source_dir()]
  )
endif

subdir('icons')
