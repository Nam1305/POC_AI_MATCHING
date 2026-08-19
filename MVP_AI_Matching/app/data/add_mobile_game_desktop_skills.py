"""Add mobile, game, and desktop-app domain skills to the matching taxonomy.

The existing dataset (Stack Overflow tag scrape) already covers most classic
mobile/game/desktop tags (android-*, ios*, swift*, unity-game-engine,
unreal-engine, wpf, winforms, javafx, swing, qt*, ...). This migration fills
in the modern/current gaps: platform integration APIs (CarPlay, Android Auto,
HomeKit, WidgetKit, ...), current game engines/tools (GameMaker, Cocos
Creator, Construct 3, ...), and current cross-platform desktop UI stacks
(Avalonia, WinUI, Uno Platform, Compose Multiplatform, Wails).

This is a one-time, idempotent data migration. It intentionally adds only
conservative implication edges (a framework implies its host language/
platform), matching the pattern used by the other add_*_skills.py scripts.

Run from the repository root:
    python3 app/data/add_mobile_game_desktop_skills.py
    python3 app/data/close_implies.py
"""

from __future__ import annotations

import json
from pathlib import Path


DATA_DIR = Path(__file__).parent
SKILL_DATA_FILE = DATA_DIR / "skill_data.json"
IMPLIES_FILE = DATA_DIR / "skill_implies.json"

CANONICAL_SKILLS: set[str] = {
    # Mobile platform integration APIs
    "android-auto",
    "app-clips",
    "background-fetch",
    "carplay",
    "core-motion",
    "firebase-cloud-messaging",
    "homekit",
    "push-kit",
    "universal-links",
    "widgetkit",
    # Game engines and tools
    "cocos-creator",
    "construct-3",
    "gamemaker",
    "metal-performance-shaders",
    "rpg-maker",
    # Desktop app frameworks
    "avalonia",
    "compose-multiplatform",
    "uno-platform",
    "wails",
    "windows-app-sdk",
    "winui",
}

ALIASES: dict[str, str] = {
    "avaloniaui": "avalonia",
    "babylon.js": "babylonjs",
    "game-maker-studio": "gamemaker",
    "opengl-es-3.0": "opengl-es",
    "phaser": "phaser-framework",
    "photon-engine": "photon",
    "roblox-lua": "roblox",
    "spritekit": "sprite-kit",
    "winui3": "winui",
}

IMPLIES: dict[str, list[str]] = {
    "android-auto": ["android"],
    "app-clips": ["ios"],
    "avalonia": ["c#", ".net", "linq"],
    "background-fetch": ["ios"],
    "carplay": ["ios"],
    "cocos-creator": ["javascript"],
    "compose-multiplatform": ["kotlin", "java"],
    "core-motion": ["ios"],
    "firebase-cloud-messaging": ["firebase"],
    "homekit": ["ios"],
    "metal-performance-shaders": ["metal"],
    "push-kit": ["huawei-mobile-services"],
    "uno-platform": ["c#", ".net", "linq"],
    "universal-links": ["ios"],
    "wails": ["go"],
    "widgetkit": ["swiftui", "ios"],
    "windows-app-sdk": ["c#", ".net", "linq"],
    "winui": ["c#", ".net", "linq"],
}


def is_canonical(skill_data: dict[str, str | None], name: str) -> bool:
    return name in skill_data and skill_data[name] in (None, name)


def main() -> int:
    skill_data: dict[str, str | None] = json.loads(
        SKILL_DATA_FILE.read_text(encoding="utf-8")
    )
    implies: dict[str, list[str]] = json.loads(
        IMPLIES_FILE.read_text(encoding="utf-8")
    )

    added_canonical = added_aliases = added_edges = 0
    errors: list[str] = []

    for name in sorted(CANONICAL_SKILLS):
        if name not in skill_data:
            skill_data[name] = None
            added_canonical += 1
        elif not is_canonical(skill_data, name):
            errors.append(f"{name!r} exists but is not canonical: {skill_data[name]!r}")

    for alias, canonical in ALIASES.items():
        if not is_canonical(skill_data, canonical):
            errors.append(f"alias target {canonical!r} is not canonical")
        elif alias not in skill_data:
            skill_data[alias] = canonical
            added_aliases += 1

    for source, targets in IMPLIES.items():
        if not is_canonical(skill_data, source):
            errors.append(f"implies source {source!r} is not canonical")
            continue
        for target in targets:
            if not is_canonical(skill_data, target):
                errors.append(f"implies target {target!r} is not canonical")

    if errors:
        print("Data invariant errors; no files written:")
        for error in errors:
            print(f"  {error}")
        return 1

    for source, targets in IMPLIES.items():
        current = implies.setdefault(source, [])
        for target in targets:
            if target not in current:
                current.append(target)
                added_edges += 1

    SKILL_DATA_FILE.write_text(
        json.dumps(skill_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    IMPLIES_FILE.write_text(
        json.dumps(implies, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "Added "
        f"{added_canonical} canonical skills, {added_aliases} aliases, "
        f"and {added_edges} implication edges."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
