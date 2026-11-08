"""Light and dark look for every page.

Streamlit cannot switch themes for one visitor, so the "Dark mode" switch in
the sidebar works by adding our own style rules (CSS) on top of the page.
The rules below never change; only the colors in PALETTES do.

Known limit: big scrollable tables (st.dataframe) are drawn as images, so
these rules cannot recolor them. Short tables use st.table instead, which
follows the theme.
"""
import streamlit as st

# Each mode uses the same names, so the style rules work for both.
# Chart colors were checked with a color-blind and contrast validator.
PALETTES = {
    "light": {
        "page": "#F6F7F9",       # page background
        "surface": "#FFFFFF",    # sidebar, cards, inputs
        "ink": "#1B1D23",        # main text
        "muted": "#676C78",      # secondary text, captions, axis labels
        "line": "#E3E5EA",       # borders and dividers
        "grid": "#ECEEF2",       # chart gridlines
        "accent": "#4F46E5",     # indigo: the one strong color
        "gray": "#8C92A0",       # chart color for "not highlighted"
    },
    "dark": {
        "page": "#14161B",
        "surface": "#1C1F26",
        "ink": "#E9EBF0",
        "muted": "#9CA1AD",
        "line": "#2B2F38",
        "grid": "#262A32",
        "accent": "#7F7AF3",
        "gray": "#757B8B",
    },
}

# The style rules. var(--page) and the rest are filled in from the palette above.
# Each rule targets a stable Streamlit name (data-testid), so it is easy to find.
STYLE_RULES = """
/* Page and header */
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stBottom"] > div {
    background: var(--page);
    color: var(--ink);
}
/* Keep text in a comfortable reading width */
[data-testid="stMainBlockContainer"] { max-width: 1100px; padding-top: 3rem; }

/* Sidebar: same surface as cards, with a thin dividing line */
[data-testid="stSidebar"] { background: var(--surface); border-right: 1px solid var(--line); }

/* Text: headings, paragraphs, labels and captions */
h1, h2, h3, h4, [data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"],
[data-testid="stMetricValue"], [data-testid="stSidebarNavLink"] span, label, summary {
    color: var(--ink);
}
[data-testid="stCaptionContainer"], [data-testid="stMetricLabel"], [data-testid="stNavSectionHeader"] {
    color: var(--muted);
}
h1 { font-size: 2.6rem; font-weight: 600; letter-spacing: -0.02em; line-height: 1.15; }
h2, h3 { font-weight: 600; letter-spacing: -0.01em; }

/* Cards (st.container(border=True)) and expanders: thin line, no shadow.
   A card is a block that has a border; blocks without one are not affected. */
[data-testid="stVerticalBlock"], [data-testid="stExpander"] details {
    border-color: var(--line);
}
[data-testid="stExpander"] details { background: var(--surface); }

/* Inputs, dropdowns, file drop area */
[data-baseweb="input"], [data-baseweb="input"] input, [data-baseweb="textarea"], textarea,
[data-baseweb="select"] > div, [data-testid="stFileUploaderDropzone"] {
    background: var(--surface);
    color: var(--ink);
    border-color: var(--line);
}
/* Dropdown menus open in a separate layer at the end of the page */
[data-baseweb="popover"] ul, [data-baseweb="popover"] li { background: var(--surface); color: var(--ink); }

/* Plain buttons (not the indigo main ones) */
[data-testid^="stBaseButton-secondary"] { background: var(--surface); color: var(--ink); border-color: var(--line); }

/* Chat */
[data-testid="stChatMessage"] { background: var(--surface); border: 1px solid var(--line); }
[data-testid="stChatInput"] > div { background: var(--surface); border-color: var(--line); }

/* Plain tables (st.table) */
[data-testid="stTable"] table, [data-testid="stTable"] th, [data-testid="stTable"] td {
    background: var(--surface);
    color: var(--ink);
    border-color: var(--line);
}
[data-testid="stTable"] th { color: var(--muted); font-weight: 500; }

/* Info, warning and error boxes keep their tint; only their text follows the theme */
[data-testid="stAlertContainer"] { color: var(--ink); }
"""


def is_dark() -> bool:
    # The sidebar switch stores its value under the name "dark_mode".
    return st.session_state.get("dark_mode", False)


def palette() -> dict:
    """The colors for the mode the visitor picked."""
    if is_dark():
        return PALETTES["dark"]
    return PALETTES["light"]


def apply_theme() -> None:
    """Add the style rules to the page, using the current mode's colors."""
    variables = []
    for name, color in palette().items():
        variables.append(f"--{name}: {color};")
    css = ":root { " + " ".join(variables) + " }" + STYLE_RULES
    st.html(f"<style>{css}</style>")


def theme_toggle() -> None:
    # key="dark_mode" makes Streamlit remember the choice for this visitor.
    st.toggle("Dark mode", key="dark_mode", help="Switch between a light and a dark look.")
