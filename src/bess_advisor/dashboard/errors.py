"""Explain failures in the reader's words: what happened, what to do next.

A raw exception tells the reader nothing they can act on. Each known
failure maps to a plain sentence and concrete next steps; the original
message stays available, folded away, for whoever provides support.
"""

from __future__ import annotations

from dataclasses import dataclass

from bess_advisor.data.entsoe import TOKEN_ENV_VAR, EntsoeError
from bess_advisor.data.validation import PriceDataError
from bess_advisor.optimizer import OptimizationError


@dataclass(frozen=True)
class Explanation:
    what_happened: str
    what_to_do: list[str]
    technical_detail: str


def explain(error: Exception) -> Explanation:
    detail = f"{type(error).__name__}: {error}"
    message = str(error)

    if isinstance(error, PriceDataError):
        return Explanation(
            "Les prix de cette journée sont incomplets ou mal formés, par exemple un créneau de 15 minutes "
            "sans prix. Calculer un planning sur des données incomplètes donnerait des suggestions fausses.",
            [
                "Vérifiez que la journée demandée est terminée côté publication (résultats vers 12 h 57 la veille).",
                "Si vous utilisez un fichier, vérifiez qu'il contient tous les créneaux de la journée.",
                "Relancez la génération du tableau de bord.",
            ],
            detail,
        )
    if isinstance(error, EntsoeError) and "token" in message.lower():
        return Explanation(
            "La plateforme ENTSO-E, qui publie les prix, a refusé la connexion : la clé d'accès est absente "
            "ou invalide.",
            [
                f"Vérifiez la variable {TOKEN_ENV_VAR} (le README explique comment obtenir une clé gratuite).",
                "Relancez la génération du tableau de bord.",
            ],
            detail,
        )
    if isinstance(error, EntsoeError) and "no data" in message.lower():
        return Explanation(
            "ENTSO-E n'a pas de prix pour cette journée. Elle est peut-être trop lointaine dans le futur, "
            "ou les résultats ne sont pas encore publiés.",
            [
                "Vérifiez la date demandée.",
                "Pour le lendemain, attendez la publication des résultats (vers 12 h 57).",
            ],
            detail,
        )
    if isinstance(error, EntsoeError):
        return Explanation(
            "Les prix n'ont pas pu être récupérés auprès de la plateforme ENTSO-E.",
            ["Vérifiez votre connexion internet.", "Réessayez dans quelques minutes."],
            detail,
        )
    if isinstance(error, FileNotFoundError):
        return Explanation(
            "Le fichier de prix indiqué est introuvable.",
            ["Vérifiez le chemin du fichier.", "Relancez la génération du tableau de bord."],
            detail,
        )
    if isinstance(error, OptimizationError):
        return Explanation(
            "Le calcul du planning n'a pas abouti. C'est inhabituel et probablement lié aux paramètres de la batterie.",
            [
                "Vérifiez les paramètres de la batterie.",
                "Si le problème persiste, signalez-le avec le détail ci-dessous.",
            ],
            detail,
        )
    return Explanation(
        "Une erreur inattendue a empêché la préparation du tableau de bord.",
        ["Relancez la génération.", "Si le problème persiste, signalez-le avec le détail ci-dessous."],
        detail,
    )
