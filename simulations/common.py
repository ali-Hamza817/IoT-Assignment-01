"""Shared output paths, colour palette, plot style and media writers for all simulations."""
from pathlib import Path

import imageio.v2 as iio
import matplotlib
import numpy as np
from PIL import Image

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "media" / "figures"     # static charts (.pdf for the report, .png for the README)
FRAMES = ROOT / "media" / "frames"       # multipage frame PDFs + timelines for LaTeX `animate`
VIDEOS = ROOT / "media" / "videos"       # .mp4 videos (attached to the PDF, linked from the README)
GIFS = ROOT / "media" / "gifs"           # .gif previews shown inline in the README
RESULTS = ROOT / "results"               # numeric results (.json) quoted in the report
for folder in (FIGURES, FRAMES, VIDEOS, GIFS, RESULTS):
    folder.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- palette
SURFACE = "#fcfcfb"
INK = "#000000"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
YELLOW = "#eda100"
GREEN = "#008300"
VIOLET = "#6250d6"

GOOD = "#0ca30c"
SERIOUS = "#ec835a"
CRITICAL = "#d03b3b"

SEQ_BLUE = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
            "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
CMAP_BLUE = LinearSegmentedColormap.from_list("seqblue", SEQ_BLUE)
# residual battery: full = blue, half = grey, empty = red
CMAP_ENERGY = LinearSegmentedColormap.from_list(
    "energy", ["#d03b3b", "#ec835a", "#f0efec", "#86b6ef", "#2a78d6"])

plt.rcParams.update({
    "font.family": "Times New Roman",
    "mathtext.fontset": "stix",
    "text.color": "black",
    "font.size": 10,
    "axes.facecolor": SURFACE,
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
    "axes.edgecolor": AXIS,
    "axes.labelcolor": "black",
    "axes.titlecolor": "black",
    "axes.titlesize": 10,
    "axes.titleweight": "bold",
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.labelcolor": "black",
    "ytick.labelcolor": "black",
    "legend.frameon": False,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "lines.linewidth": 2,
    "pdf.fonttype": 42,
})


def save_figure(fig, name):
    """Save a static chart as vector PDF (report) and PNG (README), then close it."""
    fig.savefig(FIGURES / f"{name}.pdf")
    fig.savefig(FIGURES / f"{name}.png", dpi=160)
    plt.close(fig)


class FrameWriter:
    """Collects animation frames into three outputs:

    * a multipage PDF plus a timeline file, played inside the report by LaTeX `animate`;
    * an MP4 video, attached to the report and linked from the README;
    * a GIF preview, shown inline in the README.
    """

    def __init__(self, name, fps=6, dpi=110, gif_width=760):
        self.name = name
        self.fps = fps
        self.dpi = dpi
        self.gif_width = gif_width
        self.pdf = PdfPages(FRAMES / f"{name}.pdf")
        self.timeline = []
        self.video_frames = []
        self.gif_frames = []
        self.gif_durations = []

    def add(self, fig, hold=1):
        """Add a frame that stays on screen for `hold` ticks of the base frame rate."""
        self.pdf.savefig(fig)
        self.timeline.append(f":{self.fps / hold:.4g}:{len(self.timeline)}")
        fig.set_dpi(self.dpi)
        fig.canvas.draw()
        img = np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()
        h, w = img.shape[:2]
        img = img[: h - h % 2, : w - w % 2]
        self.video_frames.extend([img] * hold)
        small = Image.fromarray(img)
        small = small.resize((self.gif_width, round(small.height * self.gif_width / small.width)),
                             Image.LANCZOS)
        self.gif_frames.append(small.quantize(colors=96, method=Image.Quantize.MEDIANCUT))
        self.gif_durations.append(round(1000 * hold / self.fps))

    def close(self):
        self.pdf.close()
        (FRAMES / f"{self.name}.tln").write_text("\n".join(self.timeline) + "\n")
        iio.mimwrite(VIDEOS / f"{self.name}.mp4", self.video_frames, fps=self.fps,
                     codec="libx264", quality=8, macro_block_size=1)
        self.gif_frames[0].save(GIFS / f"{self.name}.gif", save_all=True,
                                append_images=self.gif_frames[1:], duration=self.gif_durations,
                                loop=0, optimize=True)
        print(f"[{self.name}] {len(self.timeline)} frames")
        return len(self.timeline)
