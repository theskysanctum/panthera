"""Reads the colors and fonts EmulationStation's own "menu" view would draw with - the same
<view name="menu"> section of the active theme set that ES's native Start/Space "HOME" menu
(GuiMenu) and every other ES menu screen pull from, via ThemeData::getMenuTheme() (see
es-core/src/ThemeData.cpp in batocera-emulationstation). home_overlay.py uses this so its panel
matches whatever theme set the user has installed instead of a look of its own.

This is a deliberately partial re-implementation of ES's own theme engine, not a binding to it -
there's no Python access to ES's C++ ThemeData, so <menu> colors are picked back up by parsing the
theme set's XML directly: find the active ThemeSet, inline its <include> tags the way ES does, and
read the <menuBackground name="menubg">/<menuText name="menutitle">/etc. elements a theme defines.
Anything a theme doesn't override, or any theme that fails to parse at all, falls back to ES's own
hardcoded <menu> defaults (the field initializers on ThemeData::ThemeMenu in ThemeData.h) - the
same colors ES itself would show for an entirely untouched theme.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

ES_SETTINGS = Path("/userdata/system/configs/emulationstation/es_settings.cfg")
USER_THEMES = Path("/userdata/themes")
SYSTEM_THEMES = Path("/usr/share/emulationstation/themes")
ES_RESOURCES = Path("/usr/share/emulationstation/resources")

# ES's own bundled defaults (Font.h's FONT_PATH_REGULAR, ThemeData.h's frame.png) - used whenever
# the active theme doesn't supply its own menu font/background.
DEFAULT_FONT = ES_RESOURCES / "ubuntu_condensed.ttf"
DEFAULT_FRAME = ES_RESOURCES / "frame.png"

Color = tuple[int, int, int, int]


@dataclass(slots=True)
class MenuTheme:
    title_color: Color = (0x55, 0x55, 0x55, 0xFF)
    title_selector_color: Color = (0x55, 0x55, 0x55, 0xFF)
    text_color: Color = (0x77, 0x77, 0x77, 0xFF)
    text_selected_color: Color = (0xFF, 0xFF, 0xFF, 0xFF)
    text_selector_color: Color = (0x87, 0x87, 0x87, 0xFF)
    footer_color: Color = (0xC6, 0xC6, 0xC6, 0xFF)
    background_color: Color = (0xFF, 0xFF, 0xFF, 0xFF)
    frame_path: Path = DEFAULT_FRAME
    corner_size: tuple[int, int] | None = None  # None: derive from the frame image itself
    font_path: Path | None = DEFAULT_FONT if DEFAULT_FONT.exists() else None


def _parse_color(value: str, fallback: Color) -> Color:
    value = value.strip().lstrip("#")
    if len(value) == 6:
        value += "FF"
    if len(value) != 8:
        return fallback
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4, 6))  # type: ignore[return-value]
    except ValueError:
        return fallback


def _prop(elem: ET.Element | None, tag: str) -> str | None:
    if elem is None:
        return None
    child = elem.find(tag)
    if child is None or child.text is None or not child.text.strip():
        return None
    return child.text.strip()


def _load_merged_xml(path: Path, seen: set[Path]) -> ET.Element | None:
    """Parses path, splicing in the contents of any <include> tag in place - recursively, with a
    cycle guard, the same as ES's own theme engine. Most Batocera themes keep their actual <menu>
    colors in one shared file included by every system's theme.xml, rather than repeating them."""
    path = path.resolve()
    if path in seen or not path.exists():
        return None
    seen.add(path)

    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return None

    def expand(node: ET.Element) -> None:
        for child in list(node):
            if child.tag == "include" and child.text:
                included = _load_merged_xml((path.parent / child.text.strip()).resolve(), seen)
                if included is not None:
                    index = list(node).index(child)
                    node.remove(child)
                    for offset, grandchild in enumerate(included):
                        node.insert(index + offset, grandchild)
            else:
                expand(child)

    expand(root)
    return root


def _collect_menu_elements(root: ET.Element) -> dict[str, ET.Element]:
    """Last matching <... name="..."> wins, same as ES applies an including file's own elements
    over whatever its <include>s already defined."""
    elements: dict[str, ET.Element] = {}
    for view in root.iter("view"):
        names = [n.strip() for n in (view.get("name") or "").split(",")]
        if "menu" not in names:
            continue
        for child in view:
            name = child.get("name")
            if name:
                elements[name] = child
    return elements


def _theme_set_name() -> str | None:
    try:
        root = ET.parse(ES_SETTINGS).getroot()
    except (ET.ParseError, OSError):
        return None
    node = root.find('./string[@name="ThemeSet"]')
    return node.get("value") if node is not None else None


def _theme_root(name: str) -> Path | None:
    for base in (USER_THEMES, SYSTEM_THEMES):
        candidate = base / name
        if candidate.is_dir():
            return candidate
    return None


def _representative_theme_xml(theme_root: Path) -> Path | None:
    """Any one system's theme.xml resolves the same <menu> colors as any other (they all share
    the same included file in practice) - "default" is tried first since it's the one every
    theme set is most likely to actually have."""
    default_xml = theme_root / "default" / "theme.xml"
    if default_xml.exists():
        return default_xml
    for system_dir in sorted(p for p in theme_root.iterdir() if p.is_dir()):
        candidate = system_dir / "theme.xml"
        if candidate.exists():
            return candidate
    return None


def load_menu_theme() -> MenuTheme:
    """Never raises - a theme is third-party, untrusted input from this script's point of view,
    and a broken or stripped-down one should just fall back to ES's own menu defaults rather than
    take the pause menu down with it."""
    theme = MenuTheme()

    try:
        theme_name = _theme_set_name()
        if not theme_name:
            return theme

        root_dir = _theme_root(theme_name)
        if root_dir is None:
            return theme

        xml_path = _representative_theme_xml(root_dir)
        if xml_path is None:
            return theme

        merged = _load_merged_xml(xml_path, set())
        if merged is None:
            return theme

        elements = _collect_menu_elements(merged)

        menubg = elements.get("menubg")
        bg_color = _prop(menubg, "color") or _prop(menubg, "centerColor")
        if bg_color:
            theme.background_color = _parse_color(bg_color, theme.background_color)
        bg_path = _prop(menubg, "path")
        if bg_path:
            resolved = (xml_path.parent / bg_path).resolve()
            if resolved.exists():
                theme.frame_path = resolved
        corner = _prop(menubg, "cornerSize")
        if corner:
            parts = corner.split()
            if len(parts) == 2:
                try:
                    theme.corner_size = (int(float(parts[0])), int(float(parts[1])))
                except ValueError:
                    pass

        menutitle = elements.get("menutitle")
        if _prop(menutitle, "color"):
            theme.title_color = _parse_color(_prop(menutitle, "color"), theme.title_color)
        if _prop(menutitle, "selectorColor"):
            theme.title_selector_color = _parse_color(_prop(menutitle, "selectorColor"), theme.title_selector_color)

        menufooter = elements.get("menufooter")
        if _prop(menufooter, "color"):
            theme.footer_color = _parse_color(_prop(menufooter, "color"), theme.footer_color)

        menutext = elements.get("menutext")
        if _prop(menutext, "color"):
            theme.text_color = _parse_color(_prop(menutext, "color"), theme.text_color)
        if _prop(menutext, "selectedColor"):
            theme.text_selected_color = _parse_color(_prop(menutext, "selectedColor"), theme.text_selected_color)
        if _prop(menutext, "selectorColor"):
            theme.text_selector_color = _parse_color(_prop(menutext, "selectorColor"), theme.text_selector_color)

        for key in ("menutitle", "menutext"):
            font_path = _prop(elements.get(key), "fontPath")
            if font_path:
                candidate = (xml_path.parent / font_path).resolve()
                if candidate.exists():
                    theme.font_path = candidate
                    break

        return theme
    except Exception:
        return MenuTheme()
