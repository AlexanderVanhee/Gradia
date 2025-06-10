blueprints = custom_target('blueprints',
  input: files(
    'background_selector.blp',
    'controls_overlay.blp',
    'drawing_tools_group.blp',
    'home_bar.blp',
    'image_sidebar.blp'
  ),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@']
)