import re
from typing import List, Dict, Optional

from google.colab import auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import google.auth

MEETING_NOTES = """# Product Team Sync - May 15, 2023

## Attendees
- Sarah Chen (Product Lead)
- Mike Johnson (Engineering)
- Anna Smith (Design)
- David Park (QA)

## Agenda

### 1. Sprint Review
* Completed Features
  * User authentication flow
  * Dashboard redesign
  * Performance optimization
    * Reduced load time by 40%
    * Implemented caching solution
* Pending Items
  * Mobile responsive fixes
  * Beta testing feedback integration

### 2. Current Challenges
* Resource constraints in QA team
* Third-party API integration delays
* User feedback on new UI
  * Navigation confusion
  * Color contrast issues

### 3. Next Sprint Planning
* Priority Features
  * Payment gateway integration
  * User profile enhancement
  * Analytics dashboard
* Technical Debt
  * Code refactoring
  * Documentation updates

## Action Items
- [ ] @sarah: Finalize Q3 roadmap by Friday
- [ ] @mike: Schedule technical review for payment integration
- [ ] @anna: Share updated design system documentation
- [ ] @david: Prepare QA resource allocation proposal

## Next Steps
* Schedule individual team reviews
* Update sprint board
* Share meeting summary with stakeholders

## Notes
* Next sync scheduled for May 22, 2023
* Platform demo for stakeholders on May 25
* Remember to update JIRA tickets

---
Meeting recorded by: Sarah Chen
Duration: 45 minutes
"""

# ---------- Constants & regexes ----------

DOCS_SCOPE = ["https://www.googleapis.com/auth/documents"]
INDENT_PT = 18  # ~one tab stop in Docs

ASSIGNEE_COLOR = {"red": 0.0, "green": 0.4, "blue": 0.8}
FOOTER_COLOR = {"red": 0.4, "green": 0.4, "blue": 0.4}

HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)")
CHECKBOX_RE = re.compile(r"^\s*[-*]\s+\[ \]\s+(.+)")
BULLET_RE = re.compile(r"^\s*[-*]\s+(.+)")
ASSIGNEE_RE = re.compile(r"@[^:\s]+(?=:)")


# ---------- Helpers ----------

def get_docs_service():
    """Authenticate in Colab and return docs API service"""
    print("Authenticating with Google...")
    auth.authenticate_user()
    creds, _ = google.auth.default(scopes=DOCS_SCOPE)
    return build("docs", "v1", credentials=creds)


def extract_title(md_text: str) -> str:
    """Use first H1 (# ...) line as the document title"""
    for line in md_text.splitlines():
        m = HEADING_RE.match(line.strip())
        if m and len(m.group(1)) == 1:  # only #, not ## or ###
            return m.group(2).strip()
    return "Untitled Document"


def parse_markdown(md_text: str) -> List[Dict]:
    """
    Very simple markdown parser:
      - # / ## / ### → heading1/2/3
      - - [ ] / * [ ] → checkbox
      - - ... / * ... → bullet
      - blank line → blank
      - everything else → paragraph
    """
    blocks: List[Dict] = []
    for line in md_text.splitlines():
        raw = line
        stripped = line.strip()

        if not stripped or stripped == "---":
            blocks.append({"type": "blank", "text": ""})
            continue

        m = HEADING_RE.match(stripped)
        if m:
            level = len(m.group(1))
            blocks.append({"type": f"heading{level}", "text": m.group(2).strip()})
            continue

        m = CHECKBOX_RE.match(raw)
        if m:
            leading = len(raw) - len(raw.lstrip(" "))
            level = leading // 2
            blocks.append(
                {"type": "checkbox", "text": m.group(1).strip(), "level": level}
            )
            continue

        m = BULLET_RE.match(raw)
        if m:
            leading = len(raw) - len(raw.lstrip(" "))
            level = leading // 2
            blocks.append(
                {"type": "bullet", "text": m.group(1).strip(), "level": level}
            )
            continue

        blocks.append({"type": "paragraph", "text": stripped})

    return blocks


def build_insert_requests(blocks: List[Dict]) -> List[Dict]:
    """Insert each block as a separate line; formatting comes later"""
    requests: List[Dict] = []
    index = 1  # Docs uses 1-based indices

    for block in blocks:
        text = (block.get("text") or "") + "\n"
        requests.append(
            {
                "insertText": {
                    "location": {"index": index},
                    "text": text,
                }
            }
        )
        index += len(text)

    return requests


def apply_formatting(service, document_id: str, blocks: List[Dict]) -> None:
    """Apply headings, bullets/checkboxes, assignee styling, and footer styling"""
    doc = service.documents().get(documentId=document_id).execute()
    content = doc.get("body", {}).get("content", [])

    paragraphs = []
    for elem in content:
        if "paragraph" in elem:
            paragraphs.append(
                {
                    "start": elem.get("startIndex"),
                    "end": elem.get("endIndex"),
                    "paragraph": elem["paragraph"],
                }
            )

    n = min(len(blocks), len(paragraphs))
    requests: List[Dict] = []

    for i in range(n):
        block = blocks[i]
        p = paragraphs[i]
        start, end = p["start"], p["end"]
        p_data = p["paragraph"]
        btype = block["type"]

        # ---- Headings ----
        if btype.startswith("heading"):
            style = "HEADING_1"
            if btype == "heading2":
                style = "HEADING_2"
            elif btype == "heading3":
                style = "HEADING_3"

            requests.append(
                {
                    "updateParagraphStyle": {
                        "range": {"startIndex": start, "endIndex": end},
                        "paragraphStyle": {
                            "namedStyleType": style,
                            "indentFirstLine": {"magnitude": 0, "unit": "PT"},
                            "indentStart": {"magnitude": 0, "unit": "PT"},
                        },
                        "fields": "namedStyleType,indentFirstLine,indentStart",
                    }
                }
            )
            requests.append(
                {
                    "deleteParagraphBullets": {
                        "range": {"startIndex": start, "endIndex": end}
                    }
                }
            )

        # ---- Bullets & checkboxes ----
        elif btype in ("bullet", "checkbox"):
            preset = (
                "BULLET_CHECKBOX"
                if btype == "checkbox"
                else "BULLET_DISC_CIRCLE_SQUARE"
            )
            level = block.get("level", 0)
            indent_first = level * INDENT_PT
            indent_rest = (level + 1) * INDENT_PT

            requests.append(
                {
                    "createParagraphBullets": {
                        "range": {"startIndex": start, "endIndex": end},
                        "bulletPreset": preset,
                    }
                }
            )
            requests.append(
                {
                    "updateParagraphStyle": {
                        "range": {"startIndex": start, "endIndex": end},
                        "paragraphStyle": {
                            "indentFirstLine": {
                                "magnitude": indent_first,
                                "unit": "PT",
                            },
                            "indentStart": {
                                "magnitude": indent_rest,
                                "unit": "PT",
                            },
                        },
                        "fields": "indentFirstLine,indentStart",
                    }
                }
            )

        # ---- Text-level styling: assignees + footer ----
        # Rebuild full text of this paragraph
        text = ""
        for el in p_data.get("elements", []):
            tr = el.get("textRun")
            if tr:
                text += tr.get("content", "")

        stripped = text.strip()
        if not stripped:
            continue

        # assignee (style only @name, not colon)
        for m in ASSIGNEE_RE.finditer(text):
            ostart, oend = m.start(), m.end()
            requests.append(
                {
                    "updateTextStyle": {
                        "range": {
                            "startIndex": start + ostart,
                            "endIndex": start + oend,
                        },
                        "textStyle": {
                            "bold": True,
                            "foregroundColor": {"color": {"rgbColor": ASSIGNEE_COLOR}},
                        },
                        "fields": "bold,foregroundColor",
                    }
                }
            )

        # Footer lines
        if stripped.startswith("Meeting recorded by:") or stripped.startswith("Duration:"):
            clean = text.rstrip("\n")
            length = len(clean)
            if length:
                requests.append(
                    {
                        "updateTextStyle": {
                            "range": {
                                "startIndex": start,
                                "endIndex": start + length,
                            },
                            "textStyle": {
                                "italic": True,
                                "foregroundColor": {
                                    "color": {"rgbColor": FOOTER_COLOR}
                                },
                            },
                            "fields": "italic,foregroundColor",
                        }
                    }
                )

    if requests:
        print(f"Applying {len(requests)} formatting updates...")
        service.documents().batchUpdate(
            documentId=document_id, body={"requests": requests}
        ).execute()


# ---------- Orchestrator ----------

def convert_to_google_doc(md_text: str, title: Optional[str] = None) -> Optional[str]:
    if title is None:
        title = extract_title(md_text)

    service = get_docs_service()

    try:
        print(f"Creating document: {title}")
        doc = service.documents().create(body={"title": title}).execute()
        document_id = doc["documentId"]
        print(f"Document URL: https://docs.google.com/document/d/{document_id}/edit")

        blocks = parse_markdown(md_text)
        insert_requests = build_insert_requests(blocks)
        print("Inserting content...")
        service.documents().batchUpdate(
            documentId=document_id, body={"requests": insert_requests}
        ).execute()

        print("Formatting document...")
        apply_formatting(service, document_id, blocks)

        return document_id
    except HttpError as e:
        print(f"✗ Google Docs API error: {e}")
        return None


# ---------- Run (MEETING_NOTES must be defined above) ----------

doc_id = convert_to_google_doc(MEETING_NOTES)
if doc_id:
    print("\nYour document is ready!")
    print(f"https://docs.google.com/document/d/{doc_id}/edit")
else:
    print("Document creation failed.")
