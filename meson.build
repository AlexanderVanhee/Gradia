project('gradia',
        'c',
        version: '1.4.3',
        meson_version: '>= 1.0.0',
        default_options: ['warning_level=2', 'werror=false'],
)

i18n = import('i18n')
gnome = import('gnome')
python = import('python')

# Project information
PROJECT_URL = 'https://github.com/AlexanderVanhee/Gradia'
BUGTRACKER_URL = 'https://github.com/AlexanderVanhee/Gradia/issues'
HELP_URL = 'https://github.com/AlexanderVanhee/Gradia/discussions'

# Constants
PROJECT_RDNN_NAME = 'be.alexandervanhee.gradia'
ROOT_PATH = '/be/alexandervanhee/gradia'
PKGDATA_DIR = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
MODULE_DIR =  join_paths(PKGDATA_DIR, 'gradia')

git_bin = find_program('git', required: false)

APPLICATION_ID =  PROJECT_RDNN_NAME

# Python installation directory
PY_INSTALLDIR = python.find_installation('python3')

# Check if python3 is installed
if not PY_INSTALLDIR.found()
  error('No valid python3 binary found!')
endif

conf = configuration_data()
conf.set('APP_ID', APPLICATION_ID)
conf.set('ROOT_PATH', ROOT_PATH)
conf.set('PKGDATA_DIR', PKGDATA_DIR)
conf.set('DATA_DIR', join_paths(get_option('prefix'), get_option('datadir')))
conf.set('LOCALE_DIR', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('PYTHON', PY_INSTALLDIR.full_path())
conf.set('VERSION', meson.project_version())
conf.set('BUILD_TYPE', get_option('buildtype'))
conf.set('SCHEMAS_DIR', PKGDATA_DIR)
conf.set('SOURCE_DIR', meson.current_source_dir())
conf.set('BUILD_DIR', meson.current_build_dir())


conf.set('RELEASE_VER', meson.project_version())
conf.set('PROJECT_URL', PROJECT_URL)
conf.set('BUGTRACKER_URL', BUGTRACKER_URL)
conf.set('HELP_URL', HELP_URL)

subdir('data')
subdir('gradia')
subdir('po')

gnome.post_install(
     glib_compile_schemas: true,
    gtk_update_icon_cache: true,
  update_desktop_database: true,
)
