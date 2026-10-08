project('untix',
          version: '5.0.0',
    meson_version: '>= 1.0.0',
  default_options: [ 'warning_level=2', 'werror=false', ],
)

i18n = import('i18n')
gnome = import('gnome')




subdir('data')
subdir('src')
subdir('po')

gnome.compile_resources('untix',
  'untix.gresource.xml',
  gresource_bundle: true,
  install: true,
  source_dir: ['data/resources/icons', 'src/ui', 'src', 'src/ui/pages'],
  install_dir: pkgdatadir,
)

gnome.post_install(
     glib_compile_schemas: true,
    gtk_update_icon_cache: true,
  update_desktop_database: true,
)