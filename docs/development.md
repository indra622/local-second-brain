# Development and verification

**English** | [한국어](development.ko.md)

```sh
python -m unittest discover -s tests -v
python -m compileall -q src tests examples
python -m pip check
```

Run `python tests/verify_quickstart.py` to execute the shell blocks of each README and its linked getting-started guide in
separate temporary project copies and fresh virtual environments.
The verifier starts from a disposable source copy; it does not test GitHub cloning.
These source workflows intentionally use the checkout examples. The verification checks
installation, source-byte preservation, revision history, the documented viewing commands,
and the separate reuse demo outputs.
Obsidian GUI steps are documented from official help, not independently tested.

Run `python scripts/verify_wheel.py` from the checkout to build the project wheel with
`pip wheel`, install it and its dependencies into a fresh venv without system site
packages, and smoke-test it outside the checkout with `PYTHONPATH` cleared. It proves
the package imports from that venv and exercises init, capture, curate, search, check,
review and all four read commands, including preservation of source and revision bytes.
Inputs are synthetic temporary files independent of the checkout examples; HOME and
pip cache writes stay in the temporary directory. Installation can download build tools
and dependencies; the CLI makes no runtime API calls. Temporary smoke artifacts are
removed when the check exits. This does not publish a package.

[CI](../.github/workflows/ci.yml) is configured for pull requests and pushes to `main`,
with `macos-latest` and `ubuntu-latest`, each on Python 3.11 and 3.14. Each of the four
jobs runs the full unittest suite and wheel smoke check; only macOS/Python 3.14 runs
both README source workflows. The workflow has read-only contents permission and
uses pinned official actions without persisted checkout credentials. There is no
schedule or automatic publishing.

Before this documentation reorganization, local validation on macOS with Python 3.14.6 passed all 50 unit tests, the clean wheel
smoke check, both README workflows, compilation and `pip check`.
[Hosted run 40599790644](https://github.com/indra622/local-second-brain/actions/runs/40599790644)
also passed all four macOS/Ubuntu and Python 3.11/3.14 jobs, including both README
workflows in the macOS/Python 3.14 job. This validates those hosted environments,
not every Linux distribution or the Obsidian GUI.

## Documentation validation on 2026-10-28

On macOS with Python 3.14.6, all 50 unit tests passed after this reorganization.
Both README and continuation-guide sequences passed in separate fresh virtual
environments, including the three garden revisions and synthetic reuse checks.
Compilation (`src`, `tests`, `examples`, `scripts`), `pip check`, and the relative-link
and heading checks passed. No lint or typecheck command is configured in this project.
The verifier uses a local source copy; it does not exercise the Git clone step.

The wheel check was not repeated for these documentation and verifier changes.
The earlier wheel result above is historical. Package configuration and CLI code were
unchanged. [Public-source field validation](field-validation.md) records the separate
Codex exercise and the unsuccessful Obsidian GUI access attempt.
