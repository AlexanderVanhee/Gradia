blueprints = custom_target('blueprints',
  input: files(
    'selectors/gradient_selector.blp',
    'selectors/image_selector.blp',
    'selectors/solid_selector.blp',
    'preferences/provider_list_page.blp',
    'preferences/screenshot_guide_page.blp',
    'preferences/provider_detail_page.blp',
    'preferences/custom_provider_page.blp',
    'background_selector.blp',
    'drawing_tools_group.blp',
    'image_sidebar.blp',
    'image_stack.blp',
    'main_window.blp',
    'recent_picker.blp',
    'text_entry_popover.blp',
    'welcome_page.blp',
    'preferences_window.blp',
    'confirm_close_dialog.blp',
    'image_generator_window.blp'
  ),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@']
)
