"""CLI for A-agento — AI email agent."""

from __future__ import annotations

import typer

from A import tr_multi
from A_agento.agordo import agordo_app
from A_agento.stilo import stilo_app
from A_agento.commands.email import resumu, respondi, agu
from A_agento.commands.knowledge import generi

app = typer.Typer(
    name="agento",
    help=tr_multi(
        "A-agento — AI retposta agento kun LLM",  # eo
        "A-agento — AI email agent with LLM",  # en
        "A-agento — Agent email IA avec LLM",  # fr
    ),
)
app.add_typer(agordo_app)
app.add_typer(stilo_app)

# Register AI commands
app.command(
    name="resumu",
    help=tr_multi(
        "Resumi retposxtojn kun AI",  # eo
        "Summarize emails with AI",  # en
        "Resumer les emails avec IA",  # fr
    ),
)(resumu)
app.command(
    name="respondi",
    help=tr_multi(
        "Generi inteligentan respondon al retposxto",  # eo
        "Generate smart reply to an email",  # en
        "Generer une reponse intelligente a un email",  # fr
    ),
)(respondi)

@app.command(name="respondu", hidden=True, help=tr_multi(
    "[Malrekomendita] Uzu 'agento respondi' anstataux",  # eo
    "[DEPRECATED] Use 'agento respondi' instead",  # en
    "[Deprecie] Utilisez 'agento respondi' a la place",  # fr
))
def respondu_deprecated(
    uuid: str = typer.Argument(...),
    tono: str = "courteous",
    provizanto: str | None = None,
) -> None:
    """[DEPRECATED] Use 'agento respondi' instead."""
    respondi(uuid, tono=tono, provizanto=provizanto)

app.command(
    name="agu",
    help=tr_multi(
        "Elsxi agojn el retposxto",  # eo
        "Extract actions from an email",  # en
        "Extraire des actions d'un email",  # fr
    ),
)(agu)
app.command(
    name="generi",
    help=tr_multi(
        "Generi enhavon kun AI",  # eo
        "Generate content with AI",  # en
        "Generer du contenu avec IA",  # fr
    ),
)(generi)


# Make module callable as CLI
if __name__ == "__main__":
    app()