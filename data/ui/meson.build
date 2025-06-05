blueprints = custom_target('blueprints',
  input: files(
    'image_sidebar.blp',
    'image_stack.blp',
    'main_window.blp',
    'recent_picker.blp',
    'text_entry_popover.blp',
    'welcome_page.blp'
  ),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@']
)
