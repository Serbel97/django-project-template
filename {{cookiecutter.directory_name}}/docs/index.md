# {{cookiecutter.directory_name}}

{{cookiecutter.description}}

This site is the project's documentation. Technical decisions, feature designs, and
architectural changes are captured as [Proposals](proposals/index.md) before implementation.

## Building these docs

```shell
poetry install --with docs
mkdocs serve   # live preview at http://127.0.0.1:8000
mkdocs build   # render the static site into ./site
```

See `CLAUDE.md` for the proposal workflow, or use the `/ip` skill to scaffold a new proposal.
