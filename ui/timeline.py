# ui/timeline.py
"""
Chart builders for the Timeline tab.
All functions return plotly figures that Streamlit renders with st.plotly_chart().
"""

import plotly.graph_objects as go
from collections import defaultdict


STATUS_COLORS = {
    "settled": "#27AE60",
    "active_debate": "#E74C3C",
    "fragmented": "#F39C12",
    "emerging": "#3498DB",
    "insufficient_data": "#95A5A6",
}

SHIFT_COLORS = {
    "same": "#95A5A6",
    "strengthened": "#27AE60",
    "weakened": "#F39C12",
    "reversed": "#E74C3C",
    "first_appearance": "#3498DB",
}


def build_evolution_chart(evolution: dict, topic: str) -> go.Figure:
    """
    Marker chart showing consensus shift over time.
    Each year is a point; color indicates shift direction.
    """
    positions = evolution.get("yearly_positions", [])

    if not positions:
        fig = go.Figure()
        fig.add_annotation(
            text="Not enough data for timeline",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#95A5A6")
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        return fig

    years = [p["year"] for p in positions]
    labels = [
        p["position"][:60] + "..." if len(p["position"]) > 60 else p["position"]
        for p in positions
    ]
    shifts = [p.get("shift_from_prior", "same") for p in positions]
    colors = [SHIFT_COLORS.get(s, "#95A5A6") for s in shifts]

    hover_texts = []
    for p in positions:
        ids = ", ".join(p.get("key_claim_arxiv_ids", []))
        hover_texts.append(
            f"<b>{p['year']}</b><br>"
            f"{p['position']}<br>"
            f"<i>Shift: {p.get('shift_from_prior', '?')}</i><br>"
            f"Papers: {ids}"
        )

    fig = go.Figure()

    # Connecting line
    fig.add_trace(go.Scatter(
        x=years,
        y=[1] * len(years),
        mode="lines",
        line=dict(color="#444444", width=2, dash="dot"),
        showlegend=False,
        hoverinfo="skip"
    ))

    # Year markers
    fig.add_trace(go.Scatter(
        x=years,
        y=[1] * len(years),
        mode="markers+text",
        marker=dict(size=18, color=colors, line=dict(width=2, color="white")),
        text=[str(y) for y in years],
        textposition="top center",
        hovertext=hover_texts,
        hoverinfo="text",
        showlegend=False
    ))

    # Position labels below markers
    for year, label in zip(years, labels):
        fig.add_annotation(
            x=year,
            y=0.85,
            text=label,
            showarrow=False,
            font=dict(size=10, color="#CCCCCC"),
            xanchor="center"
        )

    status = evolution.get("current_status", "unknown")
    status_color = STATUS_COLORS.get(status, "#95A5A6")

    fig.update_layout(
        title=dict(
            text=(
                f"Consensus evolution: <b>{topic}</b>  "
                f"<span style='color:{status_color}'>● {status.replace('_', ' ').title()}</span>"
            ),
            font=dict(size=14)
        ),
        xaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            range=[min(years) - 0.5, max(years) + 0.5]
        ),
        yaxis=dict(
            showgrid=False, zeroline=False,
            showticklabels=False, range=[0.5, 1.3]
        ),
        paper_bgcolor="rgba(14,17,23,0)",
        plot_bgcolor="rgba(14,17,23,0)",
        height=280,
        margin=dict(l=20, r=20, t=60, b=20)
    )

    return fig


def build_claims_per_year_bar(claims_by_year: dict, topic: str) -> go.Figure:
    """
    Bar chart: number of claims per year about a topic.
    Shows publication volume as a proxy for research activity.
    """
    if not claims_by_year:
        fig = go.Figure()
        fig.add_annotation(
            text="No claims data by year",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="#95A5A6")
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=220
        )
        return fig

    years = sorted(int(y) for y in claims_by_year.keys())
    counts = [len(claims_by_year[str(y)]) for y in years]

    fig = go.Figure(go.Bar(
        x=years,
        y=counts,
        marker_color="#4A90D9",
        hovertemplate="<b>%{x}</b><br>%{y} claims<extra></extra>"
    ))

    fig.update_layout(
        title=f"Research activity on '{topic}' by year",
        xaxis=dict(title="Year", tickmode="linear", dtick=1),
        yaxis=dict(title="Claims in graph"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(14,17,23,0.3)",
        height=220,
        margin=dict(l=20, r=20, t=50, b=20),
        font=dict(color="#CCCCCC")
    )

    return fig


def build_dispute_timeline(contradiction_timeline: dict) -> go.Figure:
    """
    Gantt-style chart showing when each dispute was active.
    Red = active, green = resolved, orange = fading.
    """
    disputes = contradiction_timeline.get("disputes", [])

    if not disputes:
        fig = go.Figure()
        fig.add_annotation(
            text="No disputes found for this topic",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="#95A5A6")
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=150
        )
        return fig

    status_color_map = {
        "active": "#E74C3C",
        "resolved": "#27AE60",
        "fading": "#F39C12"
    }

    fig = go.Figure()

    for dispute in disputes:
        start = dispute.get("first_appeared", 2020)
        end = dispute.get("resolution_year") or 2025
        status = dispute.get("status", "active")
        color = status_color_map.get(status, "#95A5A6")
        label = dispute.get("description", "")[:50]

        fig.add_trace(go.Bar(
            x=[end - start + 0.8],
            y=[label],
            base=[start],
            orientation="h",
            marker_color=color,
            marker_line_width=0,
            hovertemplate=(
                f"<b>{dispute.get('description', '')}</b><br>"
                f"First appeared: {start}<br>"
                f"Status: {status}<br>"
                f"{('Resolution: ' + str(dispute.get('resolution', ''))) if dispute.get('resolution') else ''}"
                "<extra></extra>"
            ),
            showlegend=False
        ))

    fig.update_layout(
        title="Dispute timeline",
        barmode="overlay",
        xaxis=dict(title="Year", dtick=1, range=[2019, 2026]),
        yaxis=dict(showgrid=False),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(14,17,23,0.3)",
        height=max(150, 60 + len(disputes) * 40),
        margin=dict(l=20, r=20, t=50, b=20),
        font=dict(color="#CCCCCC")
    )

    return fig