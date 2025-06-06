blueprints = custom_target('blueprints',
  input: files(
    'header_bar.blp',
    'controls_overlay.blp',
    'gradient_selector.blp',
    'home_bar.blp',
    'recent_picker.blp',
    'text_entry_popover.blp'
  ),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@']
)
