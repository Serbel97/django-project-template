# CLAUDE.md

## Project Structure

Layered architecture under `apps/`:

**`apps/api/`** — HTTP layer (request → response)
- `views/` — class-based views; secured endpoints extend `SecuredView`
  (enforces `X-Apikey` + `X-Signature` + Bearer/Basic auth)
- `forms/` — request validation with `django_api_forms` (our `Form` subclass);
  one form per operation, `Form.Create` / `Form.Update` nesting
- `filters/` — `django_filter` FilterSets for list endpoints
- `response.py`, `errors.py`, `encoders.py` — response objects
  (`SingleResponse`, `PaginationResponse`), `ProblemDetailException`, JSON encoder
- `middleware/`, `decorators.py`, `urls.py`

**`apps/core/`** — domain & business logic
- `models/` — soft-delete `BaseModel`, custom `User`, `Token`, `ApiKey`, `RecoveryCode`
- `managers/`, `querysets/` — soft delete, token expiry, etc.
- `serializers/` — **pydantic** response serializers (not DRF)
- `services/` — business logic / side effects (e.g. `NotificationEmailService`)
- `checkers/` — object-level permissions (`django-object-checker`, ABAC)
- `auth.py` — authentication backends (Bearer, Basic)

**`apps/tests/`** — test suite mirroring the above (`api/`, `services/`, `db/`).

**Request flow:** `urls → SecuredView (api key + signature + auth) → Form (validate)
→ service / model (logic) → pydantic serializer → SingleResponse / PaginationResponse`.

## Code Style

Format with **Black** (line length 119), lint with **flake8**, and type-check with **mypy**:

```bash
make format      # black .
make lint        # flake8 apps/
make typecheck   # mypy apps/
```

## Testing

Tests use Django's built-in `unittest` framework and live under `apps/tests/`
(see `apps/tests/README.md`). They run against the `test` settings and the `PG*`
environment variables; the test database is created automatically as
`test_<PGDATABASE>`.

Always run the suite with the **`apps.tests`** label (or `make test`). Bare
`manage.py test` discovers nothing (the suite is nested under the `apps/`
package), and `manage.py test apps` re-imports the models as `core.*` and fails
with a "Conflicting models" error.

```bash
# Once, if migrations have not been generated yet:
make migrations          # == python manage.py makemigrations

# Run the whole suite:
make test                # == python manage.py test apps.tests --settings={{cookiecutter.project_name}}.settings.test

# Run a subset (e.g. only the API view tests):
python manage.py test apps.tests.api --settings={{cookiecutter.project_name}}.settings.test

# Run a single test, keeping the test DB between runs for faster iteration:
python manage.py test apps.tests.api.auth.test_authentication --keepdb \
    --settings={{cookiecutter.project_name}}.settings.test
```

When adding a feature, add tests under the matching `apps/tests/` subpackage
(`api/`, `services/`, `db/`). API tests should extend `apps.tests.base.Base`,
which signs every request (`X-Apikey` + `X-Signature`) and provides
`self.authenticate(user)` for Bearer-authenticated calls.

## Proposal System

All feature development follows the **proposal-first methodology**:

1. Create proposal in `docs/proposals/posts/IP-XXX-feature-name.md` (use the `/ip` skill to scaffold it)
2. Follow template: Status, Problem Statement, Proposed Solution, Implementation Plan, Alternatives, Trade-offs
3. Proposals use mkdocs-material blog format with metadata (draft, date, authors, categories, tags)
4. Accepted proposals become implementation specifications

**Proposal Template Structure** (see `docs/proposals/.template.md`):
- Status, Problem Statement, Proposed Solution, Implementation Plan (phases with checkboxes)
- Technical Details, Alternatives Considered, Trade-offs and Risks, Open Questions, Success Criteria
- Future Considerations, References, Review Questions, Changelog

**Writing Proposals - Important Guidelines**:

1. **No Time Estimates Required**: Do NOT include implementation time estimates or effort calculations. Focus on what needs to be done, not how long it will take. Users will decide scheduling.

2. **Always Update Changelog**: When making ANY changes to a proposal (including initial creation), update the Changelog table at the bottom with:
   - Date (YYYY-MM-DD format)
   - Author (username)
   - Brief description of changes

   Example:
   ```markdown
   ## Changelog

   | Date | Author | Changes |
   |------|--------|---------|
   | 2026-01-11 | author | Initial draft |
   | 2026-01-12 | author | Refined implementation plan after review |
   ```

3. **Implementation Plan**: Focus on concrete steps and phases, not timelines. Break work into actionable checkboxes without "this will take X hours" estimates.

4. **Update Proposals Index**: When creating or changing a proposal's status, update `docs/proposals/index.md` to reflect the current state in the proposals tracking table. This index provides a quick overview of all proposals and their states.

5. **Review Questions (AI-Created Proposals)**: When an AI agent creates a proposal draft, it MUST include a "Review Questions" section before the Changelog. This section identifies potential inconsistencies, edge cases, and unresolved technical decisions that require human input before implementation.

   **Workflow**:
   - Step 1: Create complete proposal draft with all standard sections
   - Step 2: Read back the created file to verify completeness
   - Step 3: Review the proposal for inconsistencies, contradictions, edge cases, and open questions
   - Step 4: Add "Review Questions" section with identified issues
   - Step 5: Update Changelog noting "Added Review Questions section"

   **Review Questions Format** (see `docs/proposals/.template.md` for the canonical structure):
   ```markdown
   ## Review Questions

   **Status**: ⏳ Awaiting Answers
   **Review Date**: YYYY-MM-DD
   **Reviewer**: Claude AI

   The following questions must be answered before implementation:

   ---

   ### Q1: [Question Title]

   **Issue**: [Description of the problem/inconsistency with line numbers]

   **Context**: [Why this matters]

   **Question**: [The specific question to answer]

   **Options**:
   - [ ] **A**: [Option description] (recommended if applicable)
   - [ ] **B**: [Option description]
   - [ ] **C**: [Option description]

   **Answer**:
   ```
   [User fills this in]
   ```

   **Resolution**:
   ```
   [User describes how proposal will be updated]
   ```

   ---
   ```

   **What to Review For**:
   - Schema/migration inconsistencies (e.g., nullable vs required fields)
   - Contradictions between sections (e.g., "optional" in schema, "required" in discussion)
   - Edge cases not handled (e.g., empty collections, NULL values)
   - Missing implementation details (e.g., "validation needed" without specifying logic)
   - Ambiguous statements (e.g., "inherited or set directly" without HOW)
   - Incomplete migration logic (e.g., data transformation missing steps)
   - Unresolved dependencies (e.g., references to other proposals)
   - Metadata inconsistencies (e.g., date conflicts)

   **Critical vs. Non-Critical Questions**:
   - Mark as 🔴 **Critical** if it blocks implementation or causes data loss
   - Mark as ⚠️ **Medium** if it affects user experience or performance
   - Mark as ℹ️ **Low** if it's a documentation/clarity issue

**Proposal Status Values**:
- **Draft**: Initial proposal, work in progress
- **Under Review**: Proposal complete, awaiting feedback/approval
- **Accepted**: Approved for implementation
- **Implemented**: Implementation complete
- **Rejected**: Proposal declined (with rationale in proposal)
- **Superseded**: Replaced by another proposal (reference new proposal)

## Release Process

1. Update `pyproject.toml` version (Semantic Versioning)
2. Update `CHANGELOG.md` with changes (change "TBD" to release date)
3. Open a pull request against `develop`
4. Get QA approval and code review on the PR
5. A human merges the approved PR to `develop`

> **Claude must never commit or push to `develop` or `master` directly.** Always
> work on a branch and open a pull request; merging is a human decision.
