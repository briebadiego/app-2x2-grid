"""Construcción del mapa de actores (influencia x interés) en matplotlib."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLOR_ALTA_ALTA = "#d4edda"
COLOR_ALTA_BAJA = "#fff3cd"
COLOR_BAJA_ALTA = "#cce5ff"
COLOR_BAJA_BAJA = "#f8d7da"


def build_figure(df_avg, config):
    escala_min = float(config["escala_min"])
    escala_max = float(config["escala_max"])
    punto_medio = float(config["punto_medio"])

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_xlim(escala_min, escala_max)
    ax.set_ylim(escala_min, escala_max)

    ax.fill_between([punto_medio, escala_max], punto_medio, escala_max, color=COLOR_ALTA_ALTA, alpha=0.5, zorder=0)
    ax.fill_between([punto_medio, escala_max], escala_min, punto_medio, color=COLOR_ALTA_BAJA, alpha=0.5, zorder=0)
    ax.fill_between([escala_min, punto_medio], punto_medio, escala_max, color=COLOR_BAJA_ALTA, alpha=0.5, zorder=0)
    ax.fill_between([escala_min, punto_medio], escala_min, punto_medio, color=COLOR_BAJA_BAJA, alpha=0.5, zorder=0)

    ax.axvline(punto_medio, color="#6c757d", linestyle="--", linewidth=1, zorder=1)
    ax.axhline(punto_medio, color="#6c757d", linestyle="--", linewidth=1, zorder=1)

    pad = (escala_max - escala_min) * 0.02
    ax.text((punto_medio + escala_max) / 2, escala_max - pad, config["label_alta_alta"],
            ha="center", va="top", fontsize=11, fontweight="bold", color="#2c3e50")
    ax.text((punto_medio + escala_max) / 2, escala_min + pad, config["label_alta_baja"],
            ha="center", va="bottom", fontsize=11, fontweight="bold", color="#2c3e50")
    ax.text((escala_min + punto_medio) / 2, escala_max - pad, config["label_baja_alta"],
            ha="center", va="top", fontsize=11, fontweight="bold", color="#2c3e50")
    ax.text((escala_min + punto_medio) / 2, escala_min + pad, config["label_baja_baja"],
            ha="center", va="bottom", fontsize=11, fontweight="bold", color="#2c3e50")

    if not df_avg.empty:
        ax.scatter(df_avg["influencia"], df_avg["interes"], color="#343a40", s=60, zorder=3)
        for _, row in df_avg.iterrows():
            ax.annotate(row["actor"], (row["influencia"], row["interes"]),
                        textcoords="offset points", xytext=(6, 6), fontsize=9, color="#212529")

    ax.set_xlabel(config["eje_x_label"], fontsize=12)
    ax.set_ylabel(config["eje_y_label"], fontsize=12)
    ax.set_title("Mapa de actores", fontsize=14, fontweight="bold")
    fig.tight_layout()
    return fig
