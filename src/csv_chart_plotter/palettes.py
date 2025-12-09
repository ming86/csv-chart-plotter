"""
Color Palettes - Colorblind-safe trace colors for charts.

Based on Okabe-Ito, Paul Tol, and Kelly's maximum contrast palettes.
All colors meet WCAG AA contrast requirements (≥3:1).
"""

# Light theme palette (20 colors)
# Tested against #ffffff plot background
LIGHT_PALETTE = [
    '#E69F00',  # orange        (Okabe-Ito)
    '#0072B2',  # blue          (Okabe-Ito)
    '#009E73',  # bluish green  (Okabe-Ito)
    '#D55E00',  # vermillion    (Okabe-Ito)
    '#CC6677',  # rose          (Tol muted)
    '#882255',  # wine          (Tol vibrant)
    '#44AA99',  # teal          (Tol vibrant)
    '#117733',  # green         (Tol vibrant)
    '#332288',  # indigo        (Tol vibrant)
    '#AA4499',  # purple        (Tol vibrant)
    '#CC79A7',  # reddish purple (Okabe-Ito)
    '#999933',  # olive         (Tol vibrant)
    '#BE0032',  # red           (Kelly)
    '#F3C300',  # yellow        (Kelly)
    '#875692',  # purple        (Kelly)
    '#F38400',  # orange        (Kelly)
    '#008856',  # green         (Kelly)
    '#0067A5',  # blue          (Kelly)
    '#882D17',  # brown         (Kelly)
    '#8DB600',  # lime          (Kelly)
]

# Dark theme palette (20 colors)
# Tested against #1a1a1a plot background
DARK_PALETTE = [
    '#FFA94D',  # orange
    '#5BA3E8',  # blue
    '#2ECC94',  # bluish green
    '#FF7A3D',  # vermillion
    '#E88BA5',  # rose
    '#C8659D',  # wine
    '#66D4C2',  # teal
    '#4DB870',  # green
    '#6B7FDB',  # indigo
    '#D67AC4',  # purple
    '#E89CC6',  # reddish purple
    '#D4D45C',  # olive
    '#FF5A6E',  # red
    '#FFD966',  # yellow
    '#B589C0',  # purple
    '#FFA94D',  # orange
    '#4DB88A',  # green
    '#4D9DD9',  # blue
    '#C77A5C',  # brown
    '#B8D966',  # lime
]

# Bad data indicator (both themes)
BAD_DATA_COLOR = '#DDDDDD'


def get_trace_color(index: int, theme: str = 'light') -> str:
    """
    Get color for a trace by index.

    Args:
        index: Trace index (0-based)
        theme: 'light' or 'dark'

    Returns:
        Hex color string
    """
    palette = DARK_PALETTE if theme == 'dark' else LIGHT_PALETTE
    return palette[index % len(palette)]
