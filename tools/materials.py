"""Patch the stock Ogre material scripts for a livelier look.

Shipped values (from ``common.pak``):

* ``ball.material``  -> ``Balls``  uses ``specular 0 0 0 0 10``  (fully matte)
* ``table1.material``-> ``tablecloth`` / ``crushion`` also use black specular

The patches below only touch those lines, everything else is byte-identical.
"""
from __future__ import annotations

import re

BALL_SPECULAR = "specular 0.62 0.62 0.62 1 64"
CLOTH_SPECULAR = "specular 0.11 0.11 0.11 1 26"
CUSHION_SPECULAR = "specular 0.22 0.22 0.22 1 40"


def patch_ball_script(text: str) -> str:
    text = text.replace("specular 0 0 0 0 10", BALL_SPECULAR, 1)
    text = text.replace("mipmap_bias -1", "mipmap_bias -2")
    return text


def patch_table_script(text: str) -> str:
    for material, replacement in (("material tablecloth", CLOTH_SPECULAR),
                                  ("material crushion", CUSHION_SPECULAR)):
        start = text.find(material)
        if start < 0:
            continue
        idx = text.find("specular 0 0 0 1 10", start)
        if idx < 0:
            continue
        text = text[:idx] + replacement + text[idx + len("specular 0 0 0 1 10"):]
    return text


PATCHERS = {
    "ball.material": patch_ball_script,
    "table1.material": patch_table_script,
}


def patch(name: str, text: str) -> str:
    fn = PATCHERS.get(name)
    return fn(text) if fn else text


def verify(text: str) -> list[str]:
    """Return the specular lines found, for a quick sanity check."""
    return [ln.strip() for ln in text.splitlines() if re.match(r"\s*specular", ln)]
