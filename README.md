# Markdown → Google Docs Converter

A Python script for Google Colab that converts markdown meeting notes into a formatted Google Doc using the Google Docs API.

## Features

- **Markdown parsing**: Headings (H1/H2/H3), bullets, checkboxes, and paragraphs
- **Proper styling**: Nested bullets with indentation, interactive checkboxes for action items
- **Text highlighting**: `@mentions` in bold blue, footer text in italic grey
- **Auto-title extraction**: Uses first `#` heading as document title

---

## Setup & Usage

### Requirements

- Google account
- Google Colab (includes all necessary dependencies)

### Run in Colab

1. Open [Google Colab](https://colab.research.google.com/)
2. Go to **GitHub** tab and paste:
   ```
   https://github.com/usazehan/markdown-to-google-docs
   ```
3. Select `markdown_to_google_doc.ipynb`
4. **Runtime → Run all**
5. Authenticate when prompted
6. Open the generated Google Docs URL

Or simply [**click here to open in Colab**](https://colab.research.google.com/github/usazehan/markdown-to-google-docs/blob/main/markdown_to_google_doc.ipynb)

---

## Example

**Input (Markdown):**
```markdown
# Product Team Sync - May 15, 2023
## Action Items
- [ ] @sarah: Finalize Q3 roadmap by Friday
- [ ] @mike: Schedule technical review
```

**Output (Google Doc):**
- Title: "Product Team Sync - May 15, 2023" (Heading 1)
- "Action Items" (Heading 2)
- Interactive checkboxes with **@sarah** and **@mike** in bold blue

---

## How It Works

1. **Parse markdown** into structured blocks (headings, bullets, checkboxes)
2. **Insert text** into a new Google Doc
3. **Apply formatting** by fetching document paragraphs and matching blocks

---

## Code Structure

```
markdown_to_google_doc.ipynb
├── get_docs_service()          # Authentication
├── extract_title()             # Get title from first H1
├── parse_markdown()            # Parse markdown → blocks
├── build_insert_requests()     # Create text insertion requests
├── apply_formatting()          # Apply styles, bullets, checkboxes
└── convert_to_google_doc()     # Main function
```

---

## License

Provided as-is for educational purposes.
