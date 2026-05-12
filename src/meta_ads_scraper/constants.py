"""Shared scraper constants.

The card-boundary selector lives here so that both
``parsers/ad_card.py`` and ``scraper/playwright_scraper.py`` reference
the same definition. Before Phase 6 the two modules expressed the same
pattern independently, which meant a change in one could silently drift
from the other.

Selector history (Phase 3, hard-won)
====================================
Earlier xpath-only card boundary expressions (e.g. ``//div[has-library-
id-descendant and has-img-descendant and no-inner-library-id-div]``)
returned **zero** matches against Meta's live React DOM. The pattern
that actually works on production is two-step:

1. Anchor on the Library ID text node (``text=/Library ID:\\s*\\d+/``).
2. Walk up to the closest ``<div>`` that contains an ``<img>``
   (``xpath=ancestor::div[.//img][1]``).

The chained ``AD_CARD_SELECTOR`` below is the form
``scraper/playwright_scraper.py`` passes to ``page.locator(...)``. The
parser uses ``AD_CARD_BOUNDARY_XPATH`` after finding the Library ID
text node with its own ``page.get_by_text(...)`` call. The two paths
are equivalent; they must continue to agree.
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "AD_CARD_BOUNDARY_XPATH",
    "AD_CARD_SELECTOR",
]


AD_CARD_BOUNDARY_XPATH: Final[str] = "ancestor::div[.//img][1]"
"""Relative XPath from a Library ID text node up to its enclosing
ad-card ``<div>``. The card ``<div>`` is identified as the closest
ancestor containing at least one ``<img>``.
"""


AD_CARD_SELECTOR: Final[str] = rf"text=/Library ID:\s*\d+/ >> xpath={AD_CARD_BOUNDARY_XPATH}"
"""Full chained Playwright selector for one ad card. Combines a
Library-ID text anchor with the boundary XPath so that
``page.locator(AD_CARD_SELECTOR).all()`` returns one element per card.
"""
