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
