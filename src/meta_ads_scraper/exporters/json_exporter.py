from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import TextIO

from ..models import Ad


def write_ads_json(ads: Iterable[Ad], out: Path | TextIO) -> int:
    ads_list = list(ads)
    payload = [ad.model_dump(mode="json") for ad in ads_list]
    text = json.dumps(payload, indent=2, default=str)
    if isinstance(out, Path):
        out.write_text(text, encoding="utf-8")
    else:
        out.write(text)
    return len(ads_list)
