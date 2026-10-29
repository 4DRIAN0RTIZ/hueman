"""Helpers de color: contraste WCAG y clasificación oscuro/claro.

Genéricos por diseño — no dependen de ningún target ni paleta en particular,
se exponen como filtros Jinja (`contrast`, `is_dark`) a todos los templates.
"""


def _relative_luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast_text(hex_color: str) -> str:
    """Devuelve texto casi-negro o casi-blanco según la luminancia relativa
    (WCAG) del color de fondo dado, para que el contraste siempre sea legible
    sin importar qué tan clara/oscura sea la paleta del tema."""
    return "#1a1a1a" if _relative_luminance(hex_color) > 0.45 else "#f5f5f5"


def is_dark(hex_color: str) -> bool:
    """Mismo criterio de luminancia que contrast_text(), pero como booleano —
    para declarar `dark:` en temas que lo necesiten (ej. posting), ya que hay
    paletas claras (catppuccin-latte, one-light, etc.) además de las oscuras."""
    return _relative_luminance(hex_color) <= 0.45
