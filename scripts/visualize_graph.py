import os
from pathlib import Path

from analytics_copilot.workflow.graph import build_graph

data = build_graph().get_graph().draw_mermaid_png()

output = (
    Path(__file__).parent.parent
    / "src"
    / "analytics_copilot"
    / "workflow"
    / "graph-image.png"
)
output.write_bytes(data)

print(f"Saved: {os.path.relpath(output)}")
