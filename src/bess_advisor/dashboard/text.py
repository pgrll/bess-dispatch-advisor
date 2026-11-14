"""Every word the dashboard shows, and how numbers and dates are written.

The dashboard is read by market analysts and by teams outside the market
(finance, operations, management). Wording rules:

* Say what a thing means before its jargon name ("prix de la veille").
* Every number carries its unit.
* Suggestions, never orders: the decision stays with the reader.

Keeping all text here makes it reviewable in one place and translatable.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

_DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]  # fmt: skip

#: Narrow no-break space, the French thousands separator.
_THIN = " "


def french_date(day: date) -> str:
    """'samedi 18 avril 2026'."""
    return f"{_DAYS[day.weekday()]} {day.day} {_MONTHS[day.month - 1]} {day.year}"


def number(value: float, decimals: int = 0) -> str:
    """French number format: thin space for thousands, comma for decimals."""
    text = f"{abs(value):,.{decimals}f}".replace(",", _THIN).replace(".", ",")
    return ("−" if value < 0 and round(abs(value), decimals) != 0 else "") + text


def euros(value: float, signed: bool = False) -> str:
    sign = "+" if signed and value > 0 else ""
    return f"{sign}{number(value)} €"


def price(value: float) -> str:
    return f"{number(value, 2)} €/MWh"


def interval_label(start: pd.Timestamp) -> str:
    """'13:30–13:45': the 15-minute interval starting at ``start``."""
    end = start + pd.Timedelta(minutes=15)
    return f"{start:%H:%M}–{end:%H:%M}"


SCENARIO_NAMES = {
    "max_arbitrage": "Arbitrage maximal",
    "preserve": "Préservation de la batterie",
    "reserve": "Réserve pour le réseau",
}

SCENARIO_EXPLANATIONS = {
    "max_arbitrage": "Jusqu'à 2 cycles complets dans la journée, toute la puissance sert à acheter et revendre.",
    "preserve": "Un seul cycle au maximum, pour user moins la batterie.",
    "reserve": (
        "20 MW sont réservés pour aider RTE à équilibrer le réseau, contre une rémunération fixe ; "
        "les 80 MW restants achètent et revendent."
    ),
}

ACTIONS = {"charge": "Charge", "discharge": "Décharge", "idle": "Repos"}

GLOSSARY = [
    (
        "Marché de la veille (day-ahead)",
        "Enchère où l'électricité de demain est achetée et vendue aujourd'hui. "
        "Elle fixe un prix pour chaque créneau de 15 minutes du lendemain.",
    ),
    ("€/MWh", "Prix d'un mégawattheure : l'énergie d'une puissance de 1 MW pendant une heure."),
    ("Créneau", "Une période de 15 minutes. Une journée en compte 96 (92 ou 100 aux changements d'heure)."),
    (
        "Cycle",
        "Une charge complète suivie d'une décharge complète. Chaque cycle use un peu la batterie.",
    ),
    (
        "Niveau de charge",
        "L'énergie stockée dans la batterie, entre 0 et 200 MWh.",
    ),
    (
        "Écart net",
        "Ce que rapporte 1 MWh acheté puis revendu, une fois payées les pertes de conversion et l'usure.",
    ),
    (
        "Prix négatif",
        "Quand la production dépasse la demande, des producteurs paient pour injecter. "
        "Charger la batterie rapporte alors de l'argent.",
    ),
    (
        "Valeur nette",
        "Revenus de la journée moins le coût d'usure, plus la rémunération de la réserve éventuelle.",
    ),
]

DECISION_NOTE = "Ces scénarios sont des suggestions calculées. La décision de charge et de décharge reste la vôtre."

SYNTHETIC_WARNING = (
    "Données de démonstration : ces prix sont inventés pour illustrer l'outil. "
    "Ne les utilisez pas pour une décision réelle."
)

HELP_URL = "https://github.com/pgrll/bess-dispatch-advisor/issues"
