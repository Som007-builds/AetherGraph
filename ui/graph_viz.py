from pyvis.network import Network
from graph.neo4j_queries import get_all_claims, get_contradictions, get_gaps


def build_graph(output_path="ui/graph.html", min_confidence=0.0):
    net = Network(height="750px", width="100%", bgcolor="#0e1117", font_color="white")
    net.barnes_hut(spring_length=200, spring_strength=0.05)

    claims = get_all_claims()
    contradictions = get_contradictions()
    gaps = get_gaps()

    # Track what we add to avoid duplicates
    papers_added = set()
    claims_added = set()

    # Add paper nodes
    for c in claims:
        if c["arxiv_id"] not in papers_added:
            net.add_node(
                c["arxiv_id"],
                label=c["paper_title"][:25] + "...",
                color="#4A90D9",
                size=35,
                title=f"<b>{c['paper_title']}</b><br>ArXiv: {c['arxiv_id']}",
                shape="dot"
            )
            papers_added.add(c["arxiv_id"])

    # Add claim nodes + edges to their paper
    for c in claims:
        node_id = f"claim_{c['id']}"
        if node_id not in claims_added:
            net.add_node(
                node_id,
                label="",
                color="#7EC8A4",
                size=8,
                title=f"<b>Claim [{c['section']}]</b><br>{c['text']}<br><br>Confidence: {c['confidence']}",
                shape="dot"
            )
            net.add_edge(
                c["arxiv_id"], node_id,
                color="#2a2a2a", width=1
            )
            claims_added.add(node_id)

    # Add contradiction edges (red)
    for r in contradictions:
        if r["confidence"] < min_confidence:
            continue
        a_node = f"claim_{r['claim_a_id']}"
        b_node = f"claim_{r['claim_b_id']}"
        if a_node in claims_added and b_node in claims_added:
            net.add_edge(
                a_node, b_node,
                color="#E74C3C",
                width=2 + r["confidence"] * 2,
                title=f"<b>CONTRADICTS</b> (confidence: {r['confidence']:.2f})<br>{r['explanation']}",
                dashes=False
            )

    # Add gap nodes (purple)
    for g in gaps:
        gap_node = f"gap_{g['id']}"
        net.add_node(
            gap_node,
            label="GAP",
            color="#9B59B6",
            size=20,
            title=f"<b>Research Gap</b><br>{g['text']}",
            shape="diamond"
        )
        for cid in g["related_claims"]:
            claim_node = f"claim_{cid}"
            if claim_node in claims_added:
                net.add_edge(
                    claim_node, gap_node,
                    color="#9B59B6", width=1, dashes=True
                )

    net.set_options("""
    {
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -8000,
          "centralGravity": 0.3,
          "springLength": 200
        },
        "minVelocity": 0.75
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 100
      }
    }
    """)

    net.save_graph(output_path)
    print(f"Graph saved to {output_path}")
    return output_path


if __name__ == "__main__":
    build_graph()