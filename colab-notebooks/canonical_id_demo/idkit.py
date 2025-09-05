"""
idkit.py — Canonical Identifier Toolkit for CEOS DB demo

This lightweight library supports the August 2025 discussion thread 
("Acronyms for EO sensors") between Peter Strobl, George Dyke, and colleagues.

Purpose:
--------
Provide a self-contained way to generate *harmonised, persistent identifiers*
for EO entities (agency, mission, platform, instrument, sensor) following 
the proposed CEOS DB rules.

Each identifier can be minted in several "incarnations" for different use cases:
    - fullName      : up to 256 chars, human-friendly
    - shortName     : ≤32 chars, ASCII
    - acronym       : ≤16 chars, ASCII
    - mnemonic      : ≤8 chars, URI/file-safe (AWS-style)
    - flat_id       : ≤48 chars, file-name safe, dash-separated
    - hierarchical_id : ≤64 chars, structured with prefixes (A_, M_, P_, I_)

Design notes:
-------------
- Colons (:) are avoided for filename safety; only '-' and '_' are allowed.
- Mnemonics are capped at 8 chars and uniqueness is enforced without overflow.
- Configurable limits (via IdConfig) let you adjust length policies.
- Band/mode extensions are supported (e.g. MSI_B2, PALSAR_HH).
- Validation helpers check length invariants across datasets.

Intended Use:
-------------
This module is imported into the Jupyter notebook demo (`canonical_id_demo.ipynb`) 
to illustrate how CEOS DB could maintain and publish canonical identifiers, 
both for internal consistency and alignment with STAC/CDSE metadata fields.
"""


from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Dict, List, Iterable, Optional
import pandas as pd

__version__ = "0.1.0"
__all__ = [
    "IdConfig", "IdKit",
    "add_band_ids", "validate_lengths",
    # helper tokens (exported for testing/advanced users)
    "mission_token", "instrument_token",
]

# ---------- Normalisation & ID helpers ----------

SAFE_FILE_CHARS = re.compile(r'[^A-Za-z0-9\-]')   # allow letters, numbers, dash
SAFE_TAG_CHARS  = re.compile(r'[^A-Za-z0-9]')     # tightest set (mnemonics)

def _squash_spaces(s: str) -> str:
    """Collapse internal whitespace to single spaces and strip ends."""
    return re.sub(r'\s+', ' ', (s or "").strip())

def _ascii_only(s: str) -> str:
    """Remove non-ASCII codepoints (conservative for file systems/object stores)."""
    return (s or "").encode('ascii', errors='ignore').decode('ascii')

def mission_token(mission: str) -> str:
    """
    Convert a mission label to a compact token (e.g., 'Sentinel-1' -> 'SENT1').
    Tastefully compacts 'SENTINEL' -> 'SENT' to save space.
    """
    m = re.sub(r'[\s\-]+', '', mission or '').upper()
    return m.replace("SENTINEL", "SENT")

def instrument_token(instr: str) -> str:
    """Compact instrument label (e.g., 'PALSAR-2' -> 'PALSAR2')."""
    return re.sub(r'[\s\-]+', '', instr or '').upper()

def to_full_name(*parts: str, max_len: int = 256) -> str:
    """Human-friendly name with loose constraints (ASCII, ~256 chars)."""
    s = _ascii_only(_squash_spaces(" ".join([p for p in parts if p])))
    return s[:max_len]

def to_short_name(*parts: str, max_len: int = 32) -> str:
    """ASCII, filename-safe-ish label (<=32). Removes spaces; keeps dashes."""
    s = _ascii_only("-".join([(p or "").replace(" ", "") for p in parts if p]))
    s = SAFE_FILE_CHARS.sub("", s)
    return s[:max_len]

def to_acronym(parts: List[str], max_len: int = 16) -> str:
    """Acronym from first letters of tokens (<=16)."""
    tokens = []
    for p in parts:
        words = re.split(r'[\s\-/_:]+', p or "")
        head = "".join(w[:1] for w in words if w)
        tokens.append(head.upper())
    s = "_".join(t for t in tokens if t) or "ID"
    s = _ascii_only(s)[:max_len]
    return s

def to_mnemonic(parts: Iterable[str], platform_code: Optional[str], max_len: int = 8) -> str:
    """
    Minimal, file-safe slug (<=8). If platform_code is provided, ensure it
    survives at the tail even after trimming (so A/B variants differ).
    """
    core = _ascii_only("".join([(p or "").replace(" ", "") for p in parts if p]))
    core = SAFE_TAG_CHARS.sub("", core).upper()
    s = core + (platform_code or "").upper()
    return (s[:max_len] or "X")

def ensure_unique(value: str, used: Dict[str, int]) -> str:
    """
    Ensure uniqueness within a namespace by appending a numeric suffix if needed.
    Callers should enforce length caps before passing here.
    """
    base = value
    if value not in used:
        used[value] = 1
        return value
    n = used[value] + 1
    while True:
        candidate = f"{base}{n}"
        if candidate not in used:
            used[base] = n
            used[candidate] = 1
            return candidate
        n += 1

def ensure_unique_capped(value: str, used: Dict[str, int], max_len: int) -> str:
    """
    Ensure uniqueness but *guarantee* total length <= max_len by trimming
    the base to leave room for the numeric suffix.
    Example: base=SENTMSIA (8), suffix='2' -> trim to 7 and append -> SENTMSI2
    """
    base = value[:max_len] or "X"  # hard cap the base (defensive)
    if base not in used:
        used[base] = 1
        return base

    n = used[base] + 1
    while True:
        sfx = str(n)
        # leave space for the suffix
        trimmed = base[: max_len - len(sfx)]
        candidate = f"{trimmed}{sfx}"
        if candidate not in used:
            used[base] = n
            used[candidate] = 1
            return candidate
        n += 1

# ---------- Public API ----------

@dataclass
class IdConfig:
    short_max: int = 32
    acronym_max: int = 16
    mnemonic_max: int = 8
    flat_max: int = 48
    hier_max: int = 64
    include_platform_in_mnemonic: bool = True

class IdKit:
    """
    Stateful identifier minter with per-incarnation uniqueness namespaces.
    Use one IdKit per dataset/run to ensure consistent suffixing behaviour.
    """
    def __init__(self, config: IdConfig | None = None):
        self.cfg = config or IdConfig()
        self.used_short: Dict[str,int] = {}
        self.used_acro:  Dict[str,int] = {}
        self.used_mnem:  Dict[str,int] = {}
        self.used_flat:  Dict[str,int] = {}
        self.used_hier:  Dict[str,int] = {}

    def mint_row_ids(self, agency: str, mission: str, platform_code: str, instrument: str) -> Dict[str, str]:
        agency_up = (agency or "").upper()
        pc = (platform_code or "").upper()
        m_tok = mission_token(mission)
        i_tok = instrument_token(instrument)

        full  = to_full_name(agency_up, mission, pc, instrument)

        short = to_short_name(mission.replace(" ", "") if mission else "", instrument, pc, max_len=self.cfg.short_max)
        short = ensure_unique(short, self.used_short)

        acro  = to_acronym([mission, instrument, pc], max_len=self.cfg.acronym_max)
        acro  = ensure_unique(acro, self.used_acro)

        m_parts = [m_tok[:4], i_tok[:3]]
        mnem_base = to_mnemonic(
            m_parts,
            pc if self.cfg.include_platform_in_mnemonic else None,
            max_len=self.cfg.mnemonic_max
        )
        # use capped uniqueness for mnemonics
        mnem = ensure_unique_capped(mnem_base, self.used_mnem, self.cfg.mnemonic_max)

        flat = f"{agency_up}-{m_tok}-{i_tok}"
        if pc:
            flat = f"{flat}-{pc}"
        flat = SAFE_FILE_CHARS.sub("", flat)[:self.cfg.flat_max]
        flat = ensure_unique(flat, self.used_flat)

        parts = [f"A_{agency_up}", f"M_{m_tok}"]
        if pc:
            parts.append(f"P_{pc}")
        parts.append(f"I_{i_tok}")
        hier = "-".join(parts)[:self.cfg.hier_max]
        hier = ensure_unique(hier, self.used_hier)

        return {
            "fullName": full,
            "shortName": short,
            "acronym": acro,
            "mnemonic": mnem,
            "flat_id": flat,
            "hierarchical_id": hier,
        }

    def mint_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        def _apply(row: pd.Series) -> Dict[str,str]:
            return self.mint_row_ids(
                agency=row.get("agency",""),
                mission=row.get("mission",""),
                platform_code=row.get("platform_code",""),
                instrument=row.get("instrument",""),
            )
        ids = df.apply(_apply, axis=1, result_type="expand")
        return pd.concat([df.reset_index(drop=True), ids], axis=1)

def add_band_ids(df: pd.DataFrame, instrument_bands: Dict[str, List[Dict[str,str]]],
                 flat_cap: int = 64, hier_cap: int = 64) -> pd.DataFrame:
    """
    Expand instrument-level IDs to band/mode IDs using a simple instrument→bands map.
    """
    out = []
    for _, r in df.iterrows():
        bands = instrument_bands.get(r["instrument"], [])
        for b in bands:
            band_code = (b.get("band_code","") or "").upper()
            flat_ext = f"{r['flat_id']}-{band_code}"[:flat_cap]
            hier_ext = f"{r['hierarchical_id']}-B_{band_code}"[:hier_cap]
            out.append({**r, "band_code": band_code, "band_common": b.get("common",""),
                        "flat_id_band": flat_ext, "hierarchical_id_band": hier_ext})
    return pd.DataFrame(out)

def validate_lengths(df: pd.DataFrame,
                     short_max=32, acro_max=16, mnem_max=8, flat_max=48, hier_max=64) -> pd.Series:
    """Return booleans indicating whether each incarnation respects its length constraint."""
    return pd.Series({
        "flat_ok" : (df["flat_id"].str.len() <= flat_max).all(),
        "hier_ok" : (df["hierarchical_id"].str.len() <= hier_max).all(),
        "short_ok": (df["shortName"].str.len() <= short_max).all(),
        "acro_ok" : (df["acronym"].str.len()  <= acro_max).all(),
        "mnem_ok" : (df["mnemonic"].str.len() <= mnem_max).all(),
    })
