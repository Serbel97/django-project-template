---
name: ip
description: Use when quickly capturing an intellectual property idea - searches for related proposals, extends existing or creates new
user-invocable: true
argument-hint: "[NNN] <idea description>"
---

# ip — Quick proposal capture

Quickly save an Intellectual Property (IP) proposal to `docs/proposals/posts/` following the
project's proposal system (see `CLAUDE.md` for the full guidelines).

## Argument Parsing

Args format: `[NNN] <description>`

- **`/ip 002 description...`** — NNN provided → go directly to that proposal number (extend if exists, create with that number if not)
- **`/ip description...`** — no number → search by keywords, then extend or create new

Parse logic:
1. Split args on first space
2. If first token matches `^\d{3}$` → `target_number = first token`, `description = rest`
3. Otherwise → `target_number = nil`, `description = all args`

## Paths

All paths are relative to the **current working directory** (the project root). Do not hardcode absolute paths.

- Proposals dir: `docs/proposals/posts/`
- Proposal file: `docs/proposals/posts/IP-{NNN}-{slug}.md` (one file per proposal)
- Template: `docs/proposals/.template.md`
- Index: `docs/proposals/index.md`

## Author

Two distinct author fields, do not confuse them:

- **Changelog column** (`{author}`): derive from git at runtime; do not hardcode a username:
  ```sh
  git config user.name || git config user.email || echo "author"
  ```
- **Frontmatter `authors:` list**: must contain **keys defined in `docs/.authors.yml`**
  (the mkdocs-material blog plugin validates this, and each entry requires an `avatar`). Default
  to `author`. If the contributor is not yet listed, add an entry to `docs/.authors.yml` first,
  then reference its key here.

## Workflow

### Step 1: Resolve Target

**If `target_number` provided:**
- Run: `ls docs/proposals/posts/ | grep -iE "^IP-0*{target_number}-"` to find the matching file
- If found → go to **2A (Extend)**
- If not found → go to **2B (Create)** using `target_number` as the IP number

**If no `target_number`:**
- Check description for explicit "create new" / "new proposal" intent → skip search, go directly to **2B (Create)**
- Otherwise: run `ls docs/proposals/posts/` and grep filenames + file content for keywords from description
- If matches found → pick the best match and go to **2A (Extend)** automatically (no confirmation needed)
- If no matches → go to **2B (Create)**

### 2A. Extend Existing Proposal

1. Read the matched `IP-{NNN}-{slug}.md` file
2. Locate and update relevant sections:
   - Add to **Implementation Plan** (append new phase/steps as checkboxes)
   - Add supporting details to **Problem Statement**, **Proposed Solution**, or other relevant sections
3. Update **Changelog**: `| {today} | {author} | [brief change description] |`
4. Update **Status** if appropriate
5. Use the Edit tool to modify the file
6. Update `docs/proposals/index.md` tracking table if status changed
7. Confirm: `✓ Extended IP-{NNN}: [title]`

### 2B. Create New Proposal

1. Determine IP number:
   - If `target_number` provided → use it
   - Otherwise: `ls docs/proposals/posts/ | grep -oiE '^IP-[0-9]+' | grep -oE '[0-9]+' | sort -n | tail -1` → increment by 1 (start at 1 if none)
2. Format as zero-padded 3-digit: e.g. `002`
3. Derive slug from description (lowercase, hyphens, max 40 chars)
4. Read template: `docs/proposals/.template.md`
5. Create `docs/proposals/posts/IP-{NNN}-{slug}.md` with:
   - Updated frontmatter (`date: {today}`, `authors: [author]` — a key from `.authors.yml`, categories, tags)
   - A `<!-- more -->` excerpt separator after the intro (required by the blog plugin)
   - Title: `# IP-{NNN}: [Full Title]`
   - All template sections filled in
   - **Review Questions section** (required for AI-created proposals)
   - **Changelog**: `| {today} | {author} | Initial draft |`
6. Update `docs/proposals/index.md` tracking table (add row: IP number linking to the file, title, status, last updated)
7. Confirm: `✓ Created IP-{NNN}: [title]`

## Key Rules

- No time estimates in proposals
- AI-created proposals MUST include a Review Questions section
- Always update the Changelog with `YYYY-MM-DD`, author, change description
- Always update `docs/proposals/index.md`
- Derive the author from git config (see **Author** above)
