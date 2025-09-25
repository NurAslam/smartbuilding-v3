from __future__ import annotations
from typing import Dict
from fastapi import HTTPException

# Anchors: T_out_ref = 32 °C, T_in_ref = 24 °C
T_OUT_REF = 32.0
T_IN_REF  = 24.0

TABLE_NON_AC: Dict[str, float] = {
    "Insulated External Wall": 30.0,
    "Non-insulated External Wall (Shaded)": 32.0,
    "Internal Wall": 31.0,
    "Floor/Ceiling": 31.0,
    "Non-insulated External Ceiling (40% Reflective)": 41.0,
    "Insulated External Ceiling": 31.0,
    "Non-Insulated External Ceiling (80% Reflective)": 32.0,
    "SGU Window (Shaded)": 36.0,
    "DGU Window (Shaded)": 33.0,
}
TABLE_AC: Dict[str, float] = {
    "Insulated External Wall": 25.0,
    "Non-insulated External Wall (Shaded)": 29.0,
    "Internal Wall": 24.0,
    "Floor/Ceiling": 24.0,
    "Non-insulated External Ceiling (40% Reflective)": 40.0,
    "Insulated External Ceiling": 26.0,
    "Non-Insulated External Ceiling (80% Reflective)": 30.0,
    "SGU Window (Shaded)": 31.0,
    "DGU Window (Shaded)": 26.0,
}
BETA_NON_AC: Dict[str, float] = {k: 1.0 for k in TABLE_NON_AC}
BETA_AC: Dict[str, float]     = {k: 1.0 for k in TABLE_AC}


def _norm(s: str) -> str:
    return " ".join(s.strip().lower().split())


NAME_MAP = {_norm(k): k for k in TABLE_NON_AC.keys()}
ALIASES = {
    "insulated wall": "Insulated External Wall",
    "non insulated external wall shaded": "Non-insulated External Wall (Shaded)",
    "internal": "Internal Wall",
    "floor ceiling": "Floor/Ceiling",
    "ceiling 40": "Non-insulated External Ceiling (40% Reflective)",
    "ceiling 80": "Non-Insulated External Ceiling (80% Reflective)",
    "sgu window": "SGU Window (Shaded)",
    "dgu window": "DGU Window (Shaded)",
}
for a, tgt in ALIASES.items():
    NAME_MAP[_norm(a)] = tgt


def resolve_ceiling(name: str) -> str:
    key = _norm(name)
    if key in NAME_MAP:
        return NAME_MAP[key]
    raise HTTPException(400, f"Jenis ceiling '{name}' tidak dikenali. Pilih: {list(TABLE_NON_AC.keys())}")


def surface_non_ac(T_out: float, name: str) -> float:
    base = TABLE_NON_AC[name]
    beta = BETA_NON_AC[name]
    return base + (T_out - T_OUT_REF) * beta


def surface_ac(T_in: float, name: str) -> float:
    base = TABLE_AC[name]
    beta = BETA_AC[name]
    return base + (T_in - T_IN_REF) * beta
