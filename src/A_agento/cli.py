"""CLI for A-agento — AI email agent."""

from __future__ import annotations

import typer

from A import tr, tr_multi, success
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
app.command(name="resumu")(resumu)
app.command(name="respondi")(respondi)

@app.command(name="respondu", hidden=True)
def respondu_deprecated(
    uuid: str = typer.Argument(...),
    tono: str = "courteous",
    provizanto: str | None = None,
) -> None:
    """[DEPRECATED] Use 'agento respondi' instead."""
    respondi(uuid, tono=tono, provizanto=provizanto)

app.command(name="agu")(agu)
app.command(name="generi")(generi)


# Make module callable as CLI
if __name__ == "__main__":
    app()