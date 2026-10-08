pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'untix'
gnome = import('gnome')

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'untix.in',
  output: 'untix',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x'
)

untix_sources = [
  '__init__.py',
  'absences.py',
  'additional_timetables.py',
  'api.py',
  'attachment.py',
  'colors.py',
  'credentials.py',
  'create_homework.py',
  'custom_timetable_builder.py',
  'custom_timetables.py',
  'dialog.py',
  'external_page.py',
  'holiday.py',
  'homework.py',
  'homework_api.py',
  'homework_row.py',
  'information.py',
  'lesson.py',
  'login.py',
  'main.py',
  'messages.py',
  'offline_banner.py',
  'preferences.py',
  'profiles.py',
  'qr.py',
  'teachers.py',
  'timetable.py',
  'window.py',
]

install_data(untix_sources, install_dir: moduledir)
