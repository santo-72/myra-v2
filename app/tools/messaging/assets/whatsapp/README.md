# WhatsApp UI Reference Assets

This directory contains live reference screenshots captured directly from the installed WhatsApp Desktop client on this Windows PC.

Required asset filenames for PyAutoGUI matching:
- `search_box_icon.png`: The top search bar icon or placeholder text.
- `contact_result_icon.png`: The contact match indicator in the search results list.
- `compose_box_icon.png`: The text input area at the bottom of an active chat.
- `send_button_icon.png`: The send arrow icon in the chat compose bar.
- `sent_indicator.png`: The single/double checkmark appearing after successful message transmission.

When `NativeMessagingAdapter` attempts element matching, it logs which asset file was used and its match confidence.
If an asset file is absent or does not match with >= 0.8 confidence after bounded retries, explicit keyboard shortcut and coordinate fallbacks are executed and verified.
