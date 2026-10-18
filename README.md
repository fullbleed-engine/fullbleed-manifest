# Fullbleed project templates

Create an editable PDF project with Fullbleed's existing CLI. Downloads are
verified against the registry's SHA-256 hashes before extraction. The source
archives below are pinned to an immutable documentation commit.

| Template | Included project | Runtime |
| --- | --- | --- |
| `python-components` | First order document, reusable Bootstrap components, report and static catalog | Python component alpha `2.6.0a5` |
| `component-showcase` | Northstar invoice and Common Ground report in both HTML/CSS and Python components, with a live PDF preview | Python component alpha `2.6.0a5` |

Both templates are **experimental**. They use `fullbleed.ui.experimental`, whose
API may change. Template version `0.1.1` identifies the project archive; the
Fullbleed engine version is separately pinned in `requirements.txt`.
Version `0.1.0` remains available with its original archive hashes and the
`2.6.0a4` runtime pin; request it explicitly with `--version 0.1.0`.

## Create your first component PDF

Use a fresh virtual environment with CPython 3.10 or newer:

```sh
python -m venv .venv
```

Activate it with `.venv\Scripts\Activate.ps1` in Windows PowerShell, or
`source .venv/bin/activate` on macOS/Linux. Then:

```sh
python -m pip install --pre "fullbleed==2.6.0a5"
fullbleed new search components
fullbleed new remote python-components my-report --version 0.1.1
cd my-report
python first_document.py
```

Open `order.pdf`, `order.html`, and `order.unstyled.html`. Edit the rows, card
title, table columns or named-part styles in `first_document.py`, then rerun it.
The included README explains the report and catalog commands. See the
[component and styling guide](https://docs.fullbleed.dev/guides/bootstrap-components-preview/).

## Create the designed showcase

With the same alpha installed, choose a new target directory:

```sh
fullbleed new remote component-showcase my-documents --version 0.1.1
cd my-documents
python examples/design_showcase/preview.py
```

Open the local URL printed by the helper. Save Python, CSS or data edits to
refresh the PDF preview. Use `--document report` for Common Ground and
`--authoring html` for the original HTML/CSS path. The helper executes the local
Python source, binds to loopback, and stops with Ctrl-C.

To render and compare both paths:

```sh
python examples/design_showcase/compare_authoring.py --out output
```

The [paired authoring guide](https://docs.fullbleed.dev/guides/showcase-authoring/)
explains the four matching pages, reusable components, styling and HTML export.
These are fixed A4 compositions; review their layout after substantial content
growth. Bootstrap components and exported HTML use static authored states.

## Installation behavior

- `fullbleed new list` lists the active projects; `new search components` finds
  these two kits. `--dry-run --json` reports the selected archive and version.
- Installing a template copies its source and bundled assets. It does not
  install Python dependencies or run the downloaded source. If you used a
  stable Fullbleed CLI to download one of these kits, install its exact
  `requirements.txt` in a separate environment before running it.
- The target must be absent or empty. Choose another path if it contains work.
- Supported platforms can install prebuilt Fullbleed wheels. A platform without
  a compatible wheel may require a source build and native build tools.

The former `i9-stamped-vdp` entry referenced an unavailable release archive
(HTTP 404, checked October 17, 2026). It is no longer advertised as installable.
Its original metadata is retained in [legacy/i9-stamped-vdp.json](legacy/i9-stamped-vdp.json).

## Verification and updates

CI exercises the published stable `2.5.31` and alpha `2.6.0a5` CLI installers on
Windows and Linux with Python 3.10 and 3.14. It checks listing, search, version
selection for both `0.1.0` and `0.1.1`, every extracted source file, checksum
rejection for the selected latest release, preservation of
existing files, a real first PDF and edited PDF, and the paired showcase render.
Rendering the latest experimental projects explicitly uses the alpha
`2.6.0a5` environment. The older `0.1.0` archives are downloaded, checked and
extracted without executing their source on a different engine version.

The archived legacy entry is not executed or qualified for current runtimes.
Checks for the active kits establish these examples' behavior, not general
HTML/CSS, accessibility or PDF conformance.

To qualify a registry change locally:

```sh
python tools/verify_registry.py --out output/verification
```

The verifier creates isolated environments inside that new output directory,
installs the pinned public wheels and retains logs, PDFs, HTML and JSON evidence.
Use `--stable-python PATH --alpha-python PATH` to reuse prepared environments;
the alpha environment also needs `pypdf==6.19.0` for independent text checks.

Add a new template version when source bytes change. Keep existing archive URLs
and hashes intact, point `latest` to a declared release, and qualify the exact
source download through the CLI before merging. Existing engine packages and
the registry schema are unchanged.
