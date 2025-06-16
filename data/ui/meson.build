blueprints = custom_target('blueprints',
  input: files(
    'selectors/gradient_selector.blp',
    'selectors/image_selector.blp',
    'selectors/solid_selector.blp',
    'background_selector.blp',
    'controls_overlay.blp',
    'drawing_tools_group.blp',
    'image_sidebar.blp',
    'main_window.blp',
    'recent_picker.blp',
    'text_entry_popover.blp',
    'welcome_page.blp',
    'settings_window.blp',
  ),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@']
)
