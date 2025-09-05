# CEOS DB Canonical Identifier Demo

This directory contains a **self-contained demonstration** of how CEOS could generate **persistent, harmonised identifiers** for Earth Observation programmes, constellations, missions, platforms, instruments, sensors, and spectral bands.

This prototype supports the identifier concepts proposed in the **August 2025 “Acronyms for EO sensors” thread** with Peter Strobl — a concept that now informs the semantic recommendations in the **CEOS Interoperability Handbook**.

---

## Contents

| File                      | Purpose                                                           |
| ------------------------- | ----------------------------------------------------------------- |
| `canonical_id_demo.ipynb` | Jupyter Notebook demonstrating the full ID generation workflow    |
| `idkit.py`                | A lightweight Python library encapsulating the canonical ID logic |
| `export/` _(gitignored)_  | Optional folder for generated CSV/JSON exports                    |

---

## Key Features Demonstrated

- **Multiple identifier "incarnations"**:

  - `fullName` (human-readable)
  - `shortName`, `acronym`, `mnemonic` (length-constrained, ASCII-safe)
  - `flat_id`, `hierarchical_id` (file-safe paths)

- **Explicit data model separation**:

  - `programme` (e.g., Sentinel)
  - `constellation` (e.g., Sentinel-1, Sentinel-2)
  - `platform` (e.g., Sentinel-2A)
  - `sensor` vs `instrument` (distinct concrete vs class entities)

- **Uniqueness logic**: Ensures identifiers remain unique across near-duplicates (e.g. same instrument on multiple platforms).

- **Extension to bands/modes**: Supports spectral band naming (e.g., Sentinel-2 MSI B04) and SAR polarisation modes (e.g., ALOS-2 PALSAR-2 HH, HV).

- **STAC/CDSE alignment**: Demonstrates how canonical IDs slot into common STAC fields (`platform`, `instruments`, `constellation`, `sat:platform_international_designator`, etc.).

---

## Try It Out Online

Open and run the notebook directly in your browser—no setup required:

- **Google Colab** (recommended):  
  [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gamedaygeorge/ceos-db-toolkit/blob/canonical-id-demo/colab-notebooks/canonical_id_demo/canonical_id_demo.ipynb)

- **Binder** (alternative option):  
  [![Open in Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/gamedaygeorge/ceos-db-toolkit/canonical-id-demo?labpath=colab-notebooks%2Fcanonical_id_demo%2Fcanonical_id_demo.ipynb)

- **nbviewer** (read-only):  
  [View the rendered notebook](https://nbviewer.org/github/gamedaygeorge/ceos-db-toolkit/blob/canonical-id-demo/colab-notebooks/canonical_id_demo/canonical_id_demo.ipynb)

---

## Run Locally

```bash
cd ceos-db-toolkit/colab-notebooks/canonical_id_demo
python3 -m venv .venv
source .venv/bin/activate
pip install pandas jupyter

jupyter notebook
```
