"""Chart generation functions using Matplotlib."""

from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def save_absenteeism_chart(
    ranking_df: pd.DataFrame,
    output_path: str | Path,
    title: str,
) -> Path:
    """Save a bar chart of absenteeism percentages per employee from ranking DataFrame."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    valid_df = (
        ranking_df[ranking_df["absenteeism_pct"].notna()]
        if not ranking_df.empty and "absenteeism_pct" in ranking_df.columns
        else pd.DataFrame()
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    try:
        if valid_df.empty:
            ax.text(
                0.5, 0.5, "No data to display", ha="center", va="center", fontsize=14
            )
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            x = valid_df["employee_code"].astype(str)
            y = valid_df["absenteeism_pct"]
            ax.bar(x, y, color="#e74c3c", edgecolor="black", width=0.5)
            ax.set_xlabel("Employee Code")
            ax.set_ylabel("Absenteeism (%)")
            max_val = float(y.max()) if len(y) > 0 else 100.0
            ax.set_ylim(0, max(100.0, max_val + 5.0))
        ax.set_title(title)
        fig.tight_layout()
        fig.savefig(path, format="png")
    finally:
        plt.close(fig)

    return path


def save_monthly_attendance_chart(
    monthly_df: pd.DataFrame,
    output_path: str | Path,
    title: str,
) -> Path:
    """Save a bar chart of attendance percentages per month from monthly summary DataFrame."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    valid_df = (
        monthly_df[monthly_df["attendance_pct"].notna()]
        if not monthly_df.empty and "attendance_pct" in monthly_df.columns
        else pd.DataFrame()
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    try:
        if valid_df.empty:
            ax.text(
                0.5, 0.5, "No data to display", ha="center", va="center", fontsize=14
            )
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            x = valid_df["month"].astype(str)
            y = valid_df["attendance_pct"]
            ax.bar(x, y, color="#2ecc71", edgecolor="black", width=0.5)
            ax.set_xlabel("Month")
            ax.set_ylabel("Attendance (%)")
            ax.set_ylim(0, 100.0)
        ax.set_title(title)
        fig.tight_layout()
        fig.savefig(path, format="png")
    finally:
        plt.close(fig)

    return path


def save_employee_trend_chart(
    monthly_trends: list[dict],
    output_path: str | Path,
    title: str,
) -> Path:
    """Save a trend chart of monthly attendance and absenteeism percentages for an employee."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7, 4))
    try:
        valid_points = [
            m for m in monthly_trends if m.get("attendance_pct") is not None
        ]
        if not valid_points:
            ax.text(
                0.5, 0.5, "No trend data available", ha="center", va="center", fontsize=12
            )
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            labels = [m["label"] for m in valid_points]
            att_pcts = [m["attendance_pct"] for m in valid_points]
            abs_pcts = [m["absenteeism_pct"] for m in valid_points]

            ax.plot(
                labels,
                att_pcts,
                marker="o",
                color="#10b981",
                linewidth=2.5,
                label="Attendance %",
            )
            ax.plot(
                labels,
                abs_pcts,
                marker="s",
                color="#ef4444",
                linewidth=2.0,
                linestyle="--",
                label="Absenteeism %",
            )
            ax.set_ylabel("Percentage (%)")
            ax.set_ylim(0, 105.0)
            ax.grid(True, linestyle=":", alpha=0.6)
            ax.legend(loc="upper right")

        ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
        fig.tight_layout()
        fig.savefig(path, format="png", dpi=100)
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
    """Save a distribution donut/pie chart of attendance statuses for an employee."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6, 4))
    try:
        counts = [present, absent, leave, holiday]
        labels = ["Present", "Absent", "Leave", "Holiday"]
        colors = ["#10b981", "#ef4444", "#f59e0b", "#3b82f6"]

        non_zero = [(c, l, col) for c, l, col in zip(counts, labels, colors) if c > 0]

        if not non_zero:
            ax.text(
                0.5, 0.5, "No records to display", ha="center", va="center", fontsize=12
            )
            ax.set_xticks([])
            ax.set_yticks([])
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
                wedgeprops=dict(width=0.45, edgecolor="white", linewidth=2),
            )
            for t in texts:
                t.set_fontsize(10)
            for at in autotexts:
                at.set_fontsize(9)
                at.set_weight("bold")

        ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
        fig.tight_layout()
        fig.savefig(path, format="png", dpi=100)
    finally:
        plt.close(fig)

    return path

