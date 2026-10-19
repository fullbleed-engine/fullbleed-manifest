# Fullbleed project templates

Create an editable PDF project with Fullbleed's existing CLI. Downloads are
verified against the registry's SHA-256 hashes before extraction. The source
archives below are pinned to a documentation commit or an engine release and
verified against their recorded content hashes.

| Template | Included project | Runtime |
| --- | --- | --- |
| `python-components` | First order document, reusable Bootstrap components, report and static catalog | Python component alpha `2.6.0a6` |
| `component-showcase` | Northstar invoice and Common Ground report in both authoring paths, plus the accessible community guide | Python component alpha `2.6.0a8` |

Both templates are **experimental**. They use `fullbleed.ui.experimental`, whose
API may change. Project versions and engine versions are separate: the current
showcase is template `0.1.3`, while the smaller Bootstrap starter remains `0.1.2`.
Each project's `requirements.txt` pins its tested engine. All earlier template
versions remain available with their original source bytes, hashes and runtime
pins; choose one explicitly with `--version`.

## Create your first component PDF

Use a fresh virtual environment with CPython 3.10 or newer:

```sh
python -m venv .venv
```

Activate it with `.venv\Scripts\Activate.ps1` in Windows PowerShell, or
`source .venv/bin/activate` on macOS/Linux. Then:

```sh
python -m pip install --pre "fullbleed==2.6.0a6"
fullbleed new search components
fullbleed new remote python-components my-report --version 0.1.2
cd my-report
python first_document.py
```

Open `order.pdf`, `order.html`, and `order.unstyled.html`. Edit the rows, card
title, table columns or named-part styles in `first_document.py`, then rerun it.
The included README explains the report and catalog commands. See the
[component and styling guide](https://docs.fullbleed.dev/guides/bootstrap-components-preview/).

## Create the designed showcase

Use the existing stable or alpha CLI to download the current kit into a new
directory, then install its exact requirements in a virtual environment:

```sh
fullbleed new remote component-showcase my-documents --version 0.1.3
cd my-documents
python -m pip install -r requirements.txt
python design_showcase/compare_authoring.py --out output/paired
python accessible_showcase/render.py --out output/accessible-ua1
python accessible_showcase/render.py --pdf-profile pdfua2 --out output/accessible-ua2
```

The paired command creates the invoice and report through both authoring paths,
compares their PDF pages, and writes styled and unstyled HTML. The guide commands
produce `common-ground-guide.pdf` and HTML exports in their output directories.
Edit `design_showcase/data.json`, reuse the Python components, or change their
styles. Version `0.1.3` uses `design_showcase/` and `accessible_showcase/` at the
project root; older showcase kits keep their original `examples/` paths.

The [current showcase guide](https://docs.fullbleed.dev/guides/component-preview-8/)
explains the source, `class_name`, styling and export options. The invoice and
report are fixed A4 compositions; review the layout after substantial content
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

CI exercises the published stable `2.5.34` and alpha `2.6.0a8` CLI installers on
Windows and Linux with Python 3.10 and 3.14. It checks listing, search, version
selection for all seven releases across the two templates, every extracted source file, checksum
rejection for the selected latest release, preservation of
existing files, a real first PDF and edited PDF, the paired showcase render,
and both accessible-guide profiles. The Bootstrap starter renders on its pinned
`2.6.0a6`; the current showcase renders on `2.6.0a8`. Historical archives are
downloaded, checked and extracted without executing them on a different engine.

The guide PDFs must reproduce the exact hashes independently validated for the
[2.6.0a8 release](https://github.com/fullbleed-engine/fullbleed-official/releases/tag/v2.6.0a8).
Registry CI checks that reproduction and Fullbleed diagnostics; it does not run
an independent PDF/UA validator. Human assistive-technology usability remains
unverified.

The archived legacy entry is not executed or qualified for current runtimes.
Checks for the active kits establish these examples' behavior, not general
HTML/CSS, accessibility or PDF conformance.

To qualify a registry change locally:

```sh
python tools/verify_registry.py --out output/verification
```

The verifier creates isolated environments inside that new output directory,
installs the pinned public wheels and retains logs, PDFs, HTML and JSON evidence.
Use `--stable-python PATH --alpha-python PATH --bootstrap-python PATH` to reuse prepared environments;
the alpha environment also needs `pypdf==6.19.0` for independent text checks.

Add a new template version when source bytes change. Keep existing archive URLs
and hashes intact, point `latest` to a declared release, and qualify the exact
source download through the CLI before merging. Existing engine packages and
the registry schema are unchanged.
