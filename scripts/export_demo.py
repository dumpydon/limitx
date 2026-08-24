from pathlib import Path

from limitx.analytics.exports import export_artifacts
from limitx.simulation.engine import MarketSimulation


simulation = MarketSimulation(seed=42, scenario="normal")
result = simulation.run(1_000)
paths = export_artifacts(
    Path("data/demo-export"),
    simulation.book,
    simulation.journal,
    result.as_dict(),
)
print("\n".join(str(path) for path in paths))

