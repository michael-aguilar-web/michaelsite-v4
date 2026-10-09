Rather than manually editing score overlays onto my FRC match recordings, I built a React app that reads scores from official footage and automatically generate overlays.

**Features:**

- Built-in youtube video downloader for convenience
- Saveable configurations for a given event's overlay - once set up, multiple matches from that event can be processed without reconfiguring
- Robust data filtering and validation to ensure accurate score extraction
- Customizable video overlay design with animated transitions

**Built with:**

- OpenCV + Tesseract OCR
- Remotion
