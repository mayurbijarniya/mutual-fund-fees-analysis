"""The four figures in the README, rendered from the analysis output.

The palette (blue, orange, aqua) stays distinguishable under the common forms of
color blindness. Aqua is below 3:1 contrast on the background, so every series
is also labeled directly rather than by color alone. Every chart has one y-axis.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

from funds import paths  # noqa: E402

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
MUTED = "#8a8984"
GRID = "#e6e5e0"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "axes.edgecolor": GRID,
        "axes.labelcolor": TEXT_2,
        "axes.titlecolor": TEXT,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "xtick.color": TEXT_2,
        "ytick.color": TEXT_2,
        "font.size": 10,
        "legend.frameon": False,
        "legend.labelcolor": TEXT_2,
    }
)

PCT = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.1f}%")


def _save(fig, name: str) -> None:
    paths.FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(paths.FIGURES / f"{name}.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def fee_trend(table: pl.DataFrame, last_full_year: int) -> None:
    table = table.filter(pl.col("year") <= last_full_year)
    years = table["year"].to_list()
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.fill_between(
        years,
        table["p25"] * 100,
        table["p75"] * 100,
        color=SERIES[0],
        alpha=0.15,
        linewidth=0,
        label="Middle half of share classes",
    )
    ax.plot(
        years,
        table["median"] * 100,
        color=SERIES[0],
        linewidth=2,
        marker="o",
        markersize=8,
        markeredgecolor=SURFACE,
        markeredgewidth=2,
        label="Median",
    )
    for x, y in ((years[0], table["median"][0]), (years[-1], table["median"][-1])):
        ax.annotate(
            f"{y * 100:.2f}%",
            (x, y * 100),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            color=TEXT_2,
            fontsize=9,
        )
    ax.yaxis.set_major_formatter(PCT)
    ax.set_ylim(0, None)
    ax.set_ylabel("effective expense ratio")
    ax.set_title("What share classes charge, by prospectus year")
    ax.legend(loc="lower left")
    _save(fig, "fee_trend")


def within_fund(bins: pl.DataFrame, slope: float) -> None:
    x = bins["fee_gap_bin"].to_numpy() * 100
    y = bins["mean_return_gap"].to_numpy() * 100
    fig, ax = plt.subplots(figsize=(9, 4.6))
    sizes = np.clip(bins["observations"].to_numpy() / 150, 12, 220)
    ax.scatter(
        x,
        y,
        s=sizes,
        color=SERIES[0],
        edgecolor=SURFACE,
        linewidth=1.5,
        zorder=3,
        label="Share classes, grouped by fee gap",
    )
    line = np.linspace(x.min(), x.max(), 2)
    ax.plot(
        line,
        -line,
        color=MUTED,
        linestyle="--",
        linewidth=1.5,
        label="Fees fully passed through (slope -1)",
    )
    ax.plot(line, slope * line, color=SERIES[1], linewidth=2, label=f"Fitted (slope {slope:.2f})")
    ax.axhline(0, color=GRID, linewidth=1)
    ax.axvline(0, color=GRID, linewidth=1)
    ax.xaxis.set_major_formatter(PCT)
    ax.yaxis.set_major_formatter(PCT)
    ax.set_xlabel("fee relative to the fund's other share classes (percentage points)")
    ax.set_ylabel("return relative to the fund's other classes")
    ax.set_title("Same portfolio, different fee: the extra fee comes out of the return")
    ax.legend(loc="upper right")
    _save(fig, "within_fund")


def benchmark_quintiles(table: pl.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.4))
    width = 0.38
    for i, (horizon, color) in enumerate(((5, SERIES[0]), (10, SERIES[1]))):
        part = table.filter(pl.col("horizon_years") == horizon).sort("fee_quintile")
        x = part["fee_quintile"].to_numpy() + (i - 0.5) * width
        share = part["share_beating"].to_numpy() * 100
        err = [
            share - part["share_beating_low"].to_numpy() * 100,
            part["share_beating_high"].to_numpy() * 100 - share,
        ]
        ax.bar(
            x,
            share,
            width=width,
            color=color,
            edgecolor=SURFACE,
            linewidth=2,
            label=f"{horizon} years",
            yerr=err,
            error_kw={"ecolor": TEXT_2, "elinewidth": 1},
        )
        high = part["share_beating_high"].to_numpy() * 100
        for xi, s, top in zip(x, share, high, strict=True):
            ax.annotate(
                f"{s:.0f}%",
                (xi, top),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                fontsize=8,
                color=TEXT_2,
            )
    labels = []
    five = table.filter(pl.col("horizon_years") == 5).sort("fee_quintile")
    for q, fee in zip(five["fee_quintile"], five["median_fee"], strict=True):
        labels.append(f"Q{q}\n{fee * 100:.2f}% fee")
    ax.set_xticks(five["fee_quintile"].to_list(), labels, fontsize=9)
    ax.grid(axis="x", visible=False)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_ylim(0, 50)
    ax.set_ylabel("share classes that beat their own index")
    ax.set_title("The more a fund charges, the less often it beats its index")
    ax.legend(loc="upper right")
    _save(fig, "benchmark_quintiles")


def survivorship(table: pl.DataFrame, mean_bias: float) -> None:
    """The gap itself: survivors' average return minus every class's, per year.

    Plotting the two averages side by side hides a gap of a few tenths of a
    point under bars ten to twenty points tall.
    """
    years = [str(y) for y in table["year"]]
    gap = table["bias"].to_numpy() * 100
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.bar(years, gap, color=SERIES[1], edgecolor=SURFACE, linewidth=2, width=0.6)
    for x, g in zip(years, gap, strict=True):
        ax.annotate(
            f"+{g:.2f}",
            (x, g),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            color=TEXT_2,
        )
    ax.axhline(mean_bias * 100, color=MUTED, linestyle="--", linewidth=1.5)
    ax.annotate(
        f"average +{mean_bias * 100:.2f}",
        (len(years) - 0.5, mean_bias * 100),
        xytext=(0, 4),
        textcoords="offset points",
        ha="right",
        color=TEXT_2,
        fontsize=9,
    )
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, gap.max() * 1.25)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.1f}"))
    ax.set_ylabel("percentage points a year")
    ax.set_title("How much counting only surviving funds overstates the average return")
    _save(fig, "survivorship")


def render(output: dict) -> None:
    tables, results = output["tables"], output["results"]
    fee_trend(tables["fee_trend"], results["fees"]["same_class_change"]["end_year"])
    main = results["within_fund"]["main"]
    within_fund(tables["within_fund_bins"], results["within_fund"]["specifications"][main]["slope"])
    benchmark_quintiles(tables["fee_quintiles"])
    survivorship(tables["survivorship"], results["survivorship"]["mean_yearly_bias"])
