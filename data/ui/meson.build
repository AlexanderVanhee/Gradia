blueprints = custom_target('blueprints',
  input: files(
    'header_bar.blp',
    'controls_overlay.blp',
    'recent_picker.blp',
    'welcome_page.blp'
  ),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@']
)
