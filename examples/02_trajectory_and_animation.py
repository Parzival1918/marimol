import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import numpy as np

    from marimol import view_structure

    return mo, np, view_structure


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 🎬 Molecular Trajectory & Animation Recording

    This example visualizes a multi-frame molecular trajectory with interactive playback,
    timeline scrubbing, and integrated screenshot / video recording tools.
    """)
    return


@app.cell
def _(np):
    # Generate a molecular vibration trajectory for a water (H2O) molecule
    n_frames = 60
    base_o = np.array([0.0, 0.0, 0.0])
    base_h1 = np.array([0.757, 0.586, 0.0])
    base_h2 = np.array([-0.757, 0.586, 0.0])

    trajectory = []
    for i in range(n_frames):
        phase = 2 * np.pi * i / n_frames
        # Symmetric stretch and bend
        stretch = 0.12 * np.sin(phase)
        bend = 0.08 * np.cos(phase)

        h1 = base_h1 * (1.0 + stretch) + np.array([0.0, bend, 0.0])
        h2 = base_h2 * (1.0 + stretch) + np.array([0.0, bend, 0.0])
        o = base_o - np.array([0.0, bend * 0.2, 0.0])

        bond_dist_1 = float(np.linalg.norm(h1 - o))
        bond_dist_2 = float(np.linalg.norm(h2 - o))
        cos_angle = np.dot(h1 - o, h2 - o) / (bond_dist_1 * bond_dist_2)
        angle_deg = float(np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0))))

        frame = {
            "positions": [o.tolist(), h1.tolist(), h2.tolist()],
            "species": ["O", "H", "H"],
            "bonds": [{"source": 0, "target": 1}, {"source": 0, "target": 2}],
            "labels": ["O", "H1", "H2"],
            "extra_data": {
                "frame": i + 1,
                "O-H1 distance (Å)": round(bond_dist_1, 3),
                "O-H2 distance (Å)": round(bond_dist_2, 3),
                "H-O-H angle (°)": round(angle_deg, 1),
            },
        }
        trajectory.append(frame)
    return (trajectory,)


@app.cell
def _(mo):
    fps_slider = mo.ui.slider(start=1.0, stop=30.0, step=1.0, value=15.0, label="⚡ Animation FPS:")
    bg_select = mo.ui.dropdown(
        options={"Dark Blue (#0b132b)": "#0b132b", "Slate (#1e293b)": "#1e293b", "White (#ffffff)": "#ffffff"},
        value="Dark Blue (#0b132b)",
        label="🎨 Background:",
    )
    labels_toggle = mo.ui.checkbox(value=True, label="🏷️ Draw Labels")
    outlines_toggle = mo.ui.checkbox(value=True, label="✏️ Draw Outlines")

    mo.hstack([fps_slider, bg_select, labels_toggle, outlines_toggle], justify="space-between")
    return bg_select, fps_slider, labels_toggle, outlines_toggle


@app.cell
def _(
    bg_select,
    fps_slider,
    labels_toggle,
    outlines_toggle,
    trajectory,
    view_structure,
):
    viewer = view_structure(
        trajectory,
        style="ball-and-stick",
        background_color=bg_select.value,
        multi_traj=True,
        traj_fps=fps_slider.value,
        trajectory_slider=True,
        draw_labels=labels_toggle.value,
        draw_outlines=outlines_toggle.value,
        measuring_tool=True,
        recording_tools=True,
        record_include_bgd=True,
        record_include_ui=True,
        viewer_outline="1px solid #334155" if bg_select.value != "#ffffff" else "1px solid #e2e8f0",
        height="450px",
    )
    viewer
    return (viewer,)


@app.cell(hide_code=True)
def _(mo, trajectory, viewer):
    # Reactively track current frame from widget state
    current_idx = viewer.current_frame
    if current_idx < len(trajectory):
        frame_data = trajectory[current_idx]["extra_data"]
        stats = mo.hstack(
            [
                mo.stat(value=f"{current_idx + 1} / {len(trajectory)}", label="Active Frame"),
                mo.stat(value=f"{frame_data['O-H1 distance (Å)']:.3f} Å", label="O-H1 Distance"),
                mo.stat(value=f"{frame_data['H-O-H angle (°)']:.1f}°", label="H-O-H Angle"),
            ],
            justify="space-around",
        )
    else:
        stats = mo.md("Scrub timeline or play animation to inspect frame metrics.")

    mo.callout(stats, kind="neutral")
    return


if __name__ == "__main__":
    app.run()
