# Listing template

`P2PDIR-listing.txt` is a Winlink text template. It asks for one entry and writes the
listing as the message **body**, addressed to the maintainer.

- **Pat:** copy it into your Pat forms folder (`pat configure` shows `forms_path`), then
  `pat compose --template P2PDIR-listing.txt N0CVP` (the command-line composer takes the
  recipient from its argument, not the template's `To:` line), or use Pat's web composer.
- **Winlink Express:** Message → Templates → add this file as a personal template.

For a second entry, add another `entry:` line in the body before you send. Leave the note
empty to send none (delete the `note:` line).

Tried in Pat v1.0.0: `pat compose --template` into a scratch mailbox produced exactly the
canonical body, and it parses. Not yet tried in Winlink Express.
