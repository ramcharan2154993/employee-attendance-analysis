"""Chart generation functions using Matplotlib."""

from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def _absenteeism_color(val: float) -> str:
    """Return tier color for absenteeism percentage."""
    if val <= 5.0:
        return "#10b981"  # green
    if val <= 15.0:
        return "#f59e0b"  # amber
    return "#ef4444"  # red


def _attendance_color(val: float) -> str:
    """Return tier color for attendance percentage."""
    if val >= 90.0:
        return "#10b981"  # green
    if val >= 75.0:
        return "#f59e0b"  # amber
    return "#ef4444"  # red


def save_absenteeism_chart(
    ranking_df: pd.DataFrame,
    output_path: str | Path,
    title: str,
) -> Path:
    """Save a modern bar chart of absenteeism percentages per employee from ranking DataFrame."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    valid_df = (
        ranking_df[ranking_df["absenteeism_pct"].notna()]
        if not ranking_df.empty and "absenteeism_pct" in ranking_df.columns
        else pd.DataFrame()
    )

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    try:
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")

        if valid_df.empty:
            ax.text(
                0.5, 0.5, "No data to display", ha="center", va="center", fontsize=13, color="#64748b"
            )
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)
        else:
            x = valid_df["employee_code"].astype(str)
            y = valid_df["absenteeism_pct"].astype(float)
            colors = [_absenteeism_color(val) for val in y]

            bars = ax.bar(x, y, color=colors, width=0.48, edgecolor="none", zorder=3)
            ax.bar_label(bars, fmt="%.1f%%", padding=4, fontsize=9, fontweight="bold", color="#334155")

            ax.set_xlabel("Employee Code", fontsize=10, fontweight="bold", color="#475569", labelpad=8)
            ax.set_ylabel("Absenteeism (%)", fontsize=10, fontweight="bold", color="#475569", labelpad=8)
            ax.set_ylim(0, 100.0)

            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color("#cbd5e1")
            ax.spines["bottom"].set_color("#cbd5e1")

            ax.yaxis.grid(True, linestyle="--", alpha=0.55, color="#e2e8f0", zorder=0)
            ax.xaxis.grid(False)
            ax.tick_params(colors="#475569", labelsize=9)

        ax.set_title(title, loc="left", fontsize=12.5, fontweight="bold", color="#0f172a", pad=14)
        fig.tight_layout()
        fig.savefig(path, format="png", dpi=140)
    finally:
        plt.close(fig)

    return path


def save_monthly_attendance_chart(
    monthly_df: pd.DataFrame,
    output_path: str | Path,
    title: str,
) -> Path:
    """Save a modern bar chart of attendance percentages per month from monthly summary DataFrame."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    valid_df = (
        monthly_df[monthly_df["attendance_pct"].notna()]
        if not monthly_df.empty and "attendance_pct" in monthly_df.columns
        else pd.DataFrame()
    )

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    try:
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")

        if valid_df.empty:
            ax.text(
                0.5, 0.5, "No data to display", ha="center", va="center", fontsize=13, color="#64748b"
            )
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)
        else:
            x = valid_df["month"].astype(str)
            y = valid_df["attendance_pct"].astype(float)
            colors = [_attendance_color(val) for val in y]

            bars = ax.bar(x, y, color=colors, width=0.48, edgecolor="none", zorder=3)
            ax.bar_label(bars, fmt="%.1f%%", padding=4, fontsize=9, fontweight="bold", color="#334155")

            ax.set_xlabel("Month", fontsize=10, fontweight="bold", color="#475569", labelpad=8)
            ax.set_ylabel("Attendance (%)", fontsize=10, fontweight="bold", color="#475569", labelpad=8)
            ax.set_ylim(0, 100.0)

            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color("#cbd5e1")
            ax.spines["bottom"].set_color("#cbd5e1")

            ax.yaxis.grid(True, linestyle="--", alpha=0.55, color="#e2e8f0", zorder=0)
            ax.xaxis.grid(False)
            ax.tick_params(colors="#475569", labelsize=9)

        ax.set_title(title, loc="left", fontsize=12.5, fontweight="bold", color="#0f172a", pad=14)
        fig.tight_layout()
        fig.savefig(path, format="png", dpi=140)
    finally:
        plt.close(fig)

    return path


def save_employee_trend_chart(
    monthly_trends: list[dict],
    output_path: str | Path,
    title: str,
) -> Path:
    """Save a modern trend chart of monthly attendance and absenteeism percentages for an employee."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    try:
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")

        valid_points = [
            m for m in monthly_trends if m.get("attendance_pct") is not None
        ]
        if not valid_points:
            ax.text(
                0.5, 0.5, "No trend data available", ha="center", va="center", fontsize=12, color="#64748b"
            )
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)
        else:
            labels = [m["label"] for m in valid_points]
            att_pcts = [m["attendance_pct"] for m in valid_points]
            abs_pcts = [m["absenteeism_pct"] for m in valid_points]

            ax.plot(
                labels,
                att_pcts,
                marker="o",
                markersize=6,
                color="#10b981",
                linewidth=2.5,
                label="Attendance %",
                zorder=4,
            )
            ax.plot(
                labels,
                abs_pcts,
                marker="s",
                markersize=5,
                color="#ef4444",
                linewidth=2.0,
                linestyle="--",
                label="Absenteeism %",
                zorder=3,
            )
            ax.set_ylabel("Percentage (%)", fontsize=10, fontweight="bold", color="#475569", labelpad=8)
            ax.set_ylim(0, 105.0)

            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color("#cbd5e1")
            ax.spines["bottom"].set_color("#cbd5e1")

            ax.yaxis.grid(True, linestyle="--", alpha=0.55, color="#e2e8f0", zorder=0)
            ax.xaxis.grid(False)
            ax.tick_params(colors="#475569", labelsize=9)
            ax.legend(loc="upper right", frameon=True, facecolor="#ffffff", edgecolor="#e2e8f0", fontsize=9)

        ax.set_title(title, loc="left", fontsize=12, fontweight="bold", color="#0f172a", pad=12)
        fig.tight_layout()
        fig.savefig(path, format="png", dpi=140)
    finally:
        plt.close(fig)

    return path


def save_employee_distribution_chart(
    present: int,
    absent: int,
    leave: int,
    holiday: int,
    output_path: str | Path,
    title: str,
) -> Path:
    """Save a modern distribution donut chart of attendance statuses for an employee."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    try:
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")

        counts = [present, absent, leave, holiday]
        labels = ["Present", "Absent", "Leave", "Holiday"]
        colors = ["#10b981", "#ef4444", "#f59e0b", "#3b82f6"]

        non_zero = [(c, l, col) for c, l, col in zip(counts, labels, colors) if c > 0]

        if not non_zero:
            ax.text(
                0.5, 0.5, "No records to display", ha="center", va="center", fontsize=12, color="#64748b"
            )
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)
        else:
            nz_counts = [x[0] for x in non_zero]
            nz_labels = [f"{x[1]} ({x[0]})" for x in non_zero]
            nz_colors = [x[2] for x in non_zero]

            wedges, texts, autotexts = ax.pie(
                nz_counts,
                labels=nz_labels,
                autopct="%1.1f%%",
                colors=nz_colors,
                startangle=140,
                pctdistance=0.75,
                wedgeprops=dict(width=0.45, edgecolor="white", linewidth=2.5),
            )
            for t in texts:
                t.set_fontsize(9.5)
                t.set_color("#334155")
            for at in autotexts:
                at.set_fontsize(9)
                at.set_weight("bold")
                at.set_color("white")

        ax.set_title(title, loc="left", fontsize=12, fontweight="bold", color="#0f172a", pad=12)
        fig.tight_layout()
        fig.savefig(path, format="png", dpi=140)
    finally:
        plt.close(fig)

    return path


