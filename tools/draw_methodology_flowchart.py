"""Export a concise methodology diagram as PNG and editable SVG."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]


def main():
    plt.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "none"})
    fig, ax = plt.subplots(figsize=(12, 12.8))
    fig.patch.set_facecolor("white")
    ax.set(xlim=(0, 12), ylim=(0, 12.8))
    ax.axis("off")
    ink, muted, blue = "#182B3A", "#465C6D", "#356C91"

    def box(x, y, w, h, title, detail, accent=False):
        ax.add_patch(FancyBboxPatch(
            (x-w/2, y-h/2), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
            linewidth=1.15, edgecolor="#B9CEDC", facecolor="#EAF2F7" if accent else "#F7FAFC"))
        ax.text(x, y+h/2-.28, title, fontsize=13.5, weight="bold", ha="center", va="top", color=ink)
        ax.text(x, y+h/2-.65, detail, fontsize=11.2, ha="center", va="top", color=muted, linespacing=1.5)

    def arrow(x1, y1, x2, y2):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                    mutation_scale=13, linewidth=1.4, color=blue,
                                    shrinkA=0, shrinkB=2))

    def line(xs, ys):
        ax.plot(xs, ys, color=blue, linewidth=1.4, solid_capstyle="round")

    ax.text(6, 12.35, "Methodology", ha="center", va="center", fontsize=25, weight="bold", color=ink)
    ax.text(6, 11.92, "Fandom Fault Lines  |  Group 6", ha="center", fontsize=11.5, color=muted)

    box(6, 10.85, 8.6, 1.25, "1  Collect Reddit data",
        "Arctic Shift archive • Six communities • Two 28-day windows\nMarvel/DC and PS5/Xbox; StarWars and lotr for comparison")
    arrow(6, 10.205, 6, 9.90)
    box(6, 9.25, 8.6, 1.25, "2  Preprocess and organise",
        "Validate records, clean text and match accounts across communities\nResolve reply-parent authors; retain separate content and participation datasets")
    arrow(6, 8.605, 6, 8.30)
    box(6, 7.65, 8.6, 1.25, "3  Explore the data",
        "Check coverage, comment counts, active accounts and activity patterns\nCompare communities and observation windows")

    line([6, 6], [7.005, 6.67])
    line([2, 10], [6.67, 6.67])
    for x in (2, 6, 10):
        arrow(x, 6.67, x, 6.33)
    box(2, 5.40, 3.65, 1.8, "RQ1  Content",
        "Franchise mentions\nVADER sentiment\nTF-IDF and NMF topics", accent=True)
    box(6, 5.40, 3.65, 1.8, "RQ2  Network structure",
        "Directed reply graphs\nCentrality and communities\nGephi visualisation", accent=True)
    box(10, 5.40, 3.65, 1.8, "RQ3  Audience boundaries",
        "Shared accounts and overlap\nParticipation over time\nMixing between groups", accent=True)
    for x in (2, 6, 10):
        line([x, x], [4.48, 4.10])
    line([2, 10], [4.10, 4.10])
    arrow(6, 4.10, 6, 3.76)

    box(6, 3.10, 8.6, 1.25, "4  Test robustness and verify",
        "Sampling and duration sensitivity • Activity-adjusted comparisons\nAlternative graph definitions • Independent graph audits and Gephi checks")
    arrow(6, 2.455, 6, 2.12)
    box(6, 1.45, 8.6, 1.25, "5  Interpret and report",
        "Bring together evidence for all three research questions\nPresent findings, figures and limitations; identify remaining validation", accent=True)
    ax.text(6, .30, "Reply edges: replier → parent author  |  Network metrics use full graphs; display views may be filtered",
            ha="center", fontsize=9.5, color=muted)
    fig.subplots_adjust(left=.025, right=.975, bottom=.015, top=.99)
    out = ROOT / "reports/assets"
    out.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        path = out / f"methodology_flowchart.{ext}"
        fig.savefig(path, dpi=240, facecolor="white")
        print(path)
    plt.close(fig)


if __name__ == "__main__":
    main()
