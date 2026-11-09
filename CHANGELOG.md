# Changelog

## [0.13.0] - 2026-11-09

The suite's new shared look (one design system for every app, `suite-rs/design/tokens.json`):

- **Neutral greys** instead of blue-tinted backgrounds, sidebars and borders; indigo stays as the one accent colour.
- **Bigger, clearer text** on one type scale shared with the phone apps: body text 16 px, nothing smaller than 13 px;
  titles and buttons follow the same sizes everywhere (the Interface size setting still scales it all).
- The same corner radii and spacing in every app.

## [0.12.0] - 2026-11-09

Real transparency and corners that line up (suite-kit 0.10).

- **See-through windows**: where the desktop can blur what's behind a window, the main window and dialogs let it show
  through, like Windows Aero or macOS sidebars; cards stay solid. On Windows it's the system's Acrylic. On GNOME it
  needs the Blur my Shell extension (the app adds itself to its list). Switch it in Settings, Look.
- **Corners line up**: the sidebar, cards and the Settings list share one radius and one gap, and what's inside them is
  rounded to match, so the curves run side by side. The Settings header floats over the cards, as wide as them.
- The glass look's description in Settings says what it really does now.

## [0.11.0] - 2026-11-08

### Changed
- **Liquid glass done properly, the Apple way.** Backgrounds are plain again and content stays solid; the chrome is glass. Menus, drop-down lists and tooltips blur what's really under them, settings headers float over their cards and blur them as they scroll, and the sidebar floats as an inset panel. On Windows 11 the window shows the system's Mica behind the sidebar. The colour wash is gone.

## [0.10.0] - 2026-11-08

### Changed
- **A glass look on top of Material 3, with brighter colours:** frosted, see-through surfaces over a soft wash of colour. Settings turns it off; High contrast stays solid.
- **Settings is redone in the suite's new window:** sections on the left, cards of rows with switches, nothing cut off on a small screen. Every other window gets its title on top and a filled Save button.

## [0.9.0] - 2026-11-04

### Changed
- The icons are Material Symbols now: outlined, and filled for what is selected.

## [0.8.0] - 2026-11-04

### Changed
- A new look: Material 3 shapes and tonal colours, and the Manrope typeface. A flick on a trackpad now keeps gliding; a mouse wheel works as before.

## [0.7.5] - 2026-11-04

Fixed: changing the interface size and pressing Restart now works, and a button's menu opens exactly under the button (kit 0.5.3).

## [0.7.4] - 2026-10-27

Fixed: the compact text size now reaches labels, buttons, menus and lists too (the desktop theme was keeping them at the system's larger size), so the whole interface really is smaller.

## [0.7.3] - 2026-10-27

The interface is compact: smaller text (never above 9 pt), tighter spacing and smaller icons and panels, instead of the zoom the size setting used to apply. "Automatic" size is 100% again.

## [0.7.2] - 2026-10-26

The interface size set to Automatic is a compact 85% now (the shared toolkit's new standard; 80% and 90% are new choices). Larger sizes stay in Settings.

## [0.7.1] - 2026-10-26

- The interface size set to Automatic is the system's own size again (100%); the shared toolkit had made it 115%, which was too big. Larger sizes stay one choice away in Settings.

## [0.7.0] - 2026-10-26

- The look now comes from the suite's shared toolkit (the school's blue and red kept): darker text and firmer borders, larger captions, High contrast mode, and an interface size that is a little larger by default.

## [0.6.0] - 2026-10-05

- The interface is translated: Italian and Russian, with a Language setting (Italian systems start in Italian). Study content stays in the pack's language.
- Fixed: a search in the Digest said "1 key terms".

## [0.5.0] - 2026-10-02

- Pressing Enter in a one-line box now finishes with it: the cursor stops blinking and the box lets go of the focus.

## [0.4.1] - 2026-10-02

- Fixed: opening the app put a second icon on the dock instead of using the pinned one (the screen-size check forgot the app's desktop name).

## [0.4.0] - 2026-10-02
- Interface size in Settings (Automatic, 80%–130%). Automatic makes everything a little smaller on small screens such as 1366x768. Applies after a restart.
- The window never opens bigger than the screen; Settings and the pack and card editors scroll when they are taller than it.

## [0.3.0] - 2026-10-01

- Digest: a new page (Ctrl+3) that boils the whole manual down to each chapter's takeaways and key terms, in one list to scroll through. Show everything, only the takeaways or only the key terms, search across all chapters, and jump to a chapter or to its page in the manual. Practice, Glossary, Cheatsheet and Manual move one place down (Ctrl+4 to Ctrl+7).

## [0.2.0] - 2026-09-30

- Updates from inside the app: Bivouac checks GitHub about once a day and installs a new version for you (the .deb asks for your password; the Windows setup runs silently and restarts Bivouac). Switch it off or check now in Settings, or use More → Check for updates.

## [0.1.0] - 2026-09-30

First version.

- Study packs: import a Cybearly "Campo base" manual (PDF) or a pack file (.json), or start an empty pack and write your own cards. Several packs side by side, one per competition.
- Overview: countdown to the competition, today's cards, streak, two-week history and progress per chapter.
- Chapters: recap, key-concept table, self-check questions with hidden answers, sections that open the manual at the right page.
- Practice: spaced-repetition flashcards (Again/Hard/Good/Easy, keys 1–4) that make sure every card comes back before the competition day; cram mode; multiple-choice drill.
- Glossary and command cheatsheet, both searchable; built-in PDF reader for the manual.
- School branding (I.T.S. "E. Alessandrini", Montesilvano) with its colours and emblem; name, town and logo can be changed in Settings.
