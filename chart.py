"""Construcción del mapa de actores (influencia x interés) en matplotlib."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BG = "#FAFAF9"
GRID = "#E5E1DA"
AXIS = "#8A8478"

QUADRANTES = {
    "alta_alta": {"bg": "#E7F2EC", "accent": "#2F8F5B"},
    "alta_baja": {"bg": "#FBEFE1", "accent": "#C17A2E"},
    "baja_alta": {"bg": "#E8EEF7", "accent": "#39679E"},
    "baja_baja": {"bg": "#F1EAF3", "accent": "#8B5FA3"},
}


def _accent_for(influencia, interes, punto_medio):
    alta_x = influencia >= punto_medio
    alta_y = interes >= punto_medio
    if alta_x and alta_y:
        return QUADRANTES["alta_alta"]["accent"]
    if alta_x and not alta_y:
        return QUADRANTES["alta_baja"]["accent"]
    if not alta_x and alta_y:
        return QUADRANTES["baja_alta"]["accent"]
    return QUADRANTES["baja_baja"]["accent"]


def build_figure(df_avg, config, titulo="Mapa de actores"):
    escala_min = float(config["escala_min"])
    escala_max = float(config["escala_max"])
    punto_medio = float(config["punto_medio"])

    fig, ax = plt.subplots(figsize=(8, 8))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(escala_min, escala_max)
    ax.set_ylim(escala_min, escala_max)

    q = QUADRANTES
    ax.fill_between([punto_medio, escala_max], punto_medio, escala_max, color=q["alta_alta"]["bg"], zorder=0)
    ax.fill_between([punto_medio, escala_max], escala_min, punto_medio, color=q["alta_baja"]["bg"], zorder=0)
    ax.fill_between([escala_min, punto_medio], punto_medio, escala_max, color=q["baja_alta"]["bg"], zorder=0)
    ax.fill_between([escala_min, punto_medio], escala_min, punto_medio, color=q["baja_baja"]["bg"], zorder=0)

    ax.grid(True, linestyle=":", linewidth=0.6, color=GRID, zorder=0.5)
    ax.axvline(punto_medio, color=AXIS, linestyle="--", linewidth=1.2, zorder=1)
    ax.axhline(punto_medio, color=AXIS, linestyle="--", linewidth=1.2, zorder=1)

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(AXIS)

    label_box = dict(boxstyle="round,pad=0.35", facecolor="white", edgecolor="none", alpha=0.75)
    pad = (escala_max - escala_min) * 0.035
    ax.text((punto_medio + escala_max) / 2, escala_max - pad, config["label_alta_alta"],
            ha="center", va="top", fontsize=11, fontweight="bold", color=q["alta_alta"]["accent"],
            bbox=label_box, zorder=2)
    ax.text((punto_medio + escala_max) / 2, escala_min + pad, config["label_alta_baja"],
            ha="center", va="bottom", fontsize=11, fontweight="bold", color=q["alta_baja"]["accent"],
            bbox=label_box, zorder=2)
    ax.text((escala_min + punto_medio) / 2, escala_max - pad, config["label_baja_alta"],
            ha="center", va="top", fontsize=11, fontweight="bold", color=q["baja_alta"]["accent"],
            bbox=label_box, zorder=2)
    ax.text((escala_min + punto_medio) / 2, escala_min + pad, config["label_baja_baja"],
            ha="center", va="bottom", fontsize=11, fontweight="bold", color=q["baja_baja"]["accent"],
            bbox=label_box, zorder=2)

    if not df_avg.empty:
        colores = [_accent_for(r["influencia"], r["interes"], punto_medio) for _, r in df_avg.iterrows()]
        ax.scatter(df_avg["influencia"], df_avg["interes"], color=colores, s=140,
                   edgecolors="white", linewidths=1.5, zorder=3)
        for _, row in df_avg.iterrows():
            ax.annotate(
                row["actor"], (row["influencia"], row["interes"]),
                textcoords="offset points", xytext=(8, 8), fontsize=9.5, color="#2B2B2B",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#DDDAD3",
                          linewidth=0.6, alpha=0.9),
                zorder=4,
            )

    ax.set_xlabel(config["eje_x_label"], fontsize=12, color="#3A3A3A")
    ax.set_ylabel(config["eje_y_label"], fontsize=12, color="#3A3A3A")
    ax.set_title(titulo, fontsize=15, fontweight="bold", color="#232323", pad=14)
    ax.tick_params(colors=AXIS)
    fig.tight_layout()
    return fig
