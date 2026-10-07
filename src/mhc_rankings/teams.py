"""Team roster for a division, loaded from the `teams.toml` beside its games file."""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

COLOR_HEX: dict[str, str] = {
    "black": "#111111",
    "blue": "#1f5fbf",
    "green": "#1b7f3b",
    "grey": "#808080",
    "navy blue": "#001f5b",
    "red": "#c80f2e",
    "royal blue": "#2a52be",
    "white": "#ffffff",
    "yellow": "#f2c200",
}
_HEX_RE = re.compile(r"#[0-9a-fA-F]{6}")


class UnknownTeamError(ValueError):
    """Raised when a team name is not in the division's roster."""


@dataclass(frozen=True)
class Team:
    """One team: display name, short name, GameSheet page (blank if none), colors (as `#rrggbb`), and other known names."""

    name: str
    abbreviation: str
    url: str
    colors: tuple[str, ...]
    aliases: tuple[str, ...] = ()


class Roster:
    """The teams in one division, with lookup by name or alias."""

    def __init__(self, teams: list[Team], schedule_url: str = "", games_url: str = "") -> None:
        """Index `teams` by name and alias, rejecting duplicate names.

        `schedule_url` is the upcoming-games page and `games_url` the completed-games page the weekly update reads (each blank if none).
        """
        self.teams: tuple[Team, ...] = tuple(teams)
        self.schedule_url: str = schedule_url
        self.games_url: str = games_url
        self._by_name: dict[str, Team] = {}
        for team in self.teams:
            for name in (team.name, *team.aliases):
                if name in self._by_name:
                    raise ValueError(f"Duplicate team name in roster: {name!r}")
                self._by_name[name] = team

    def __len__(self) -> int:
        """Return the number of teams."""
        return len(self.teams)

    def find(self, name: str) -> Team | None:
        """Return the team known by `name`, or None when it is not in the roster."""
        return self._by_name.get(name)

    def resolve(self, name: str) -> Team:
        """Return the team known by `name` (its canonical name or an alias).

        Raises:
            UnknownTeamError: If no team matches; the message lists the known names.
        """
        try:
            return self._by_name[name]
        except KeyError:
            known = ", ".join(sorted(t.name for t in self.teams))
            raise UnknownTeamError(f"Unknown team {name!r}. Known teams: {known}") from None

    @property
    def abbreviations(self) -> dict[str, str]:
        """Map each team name and alias to the team's abbreviation."""
        return {name: t.abbreviation for name, t in self._by_name.items()}


def _color_to_hex(color: str, team: str) -> str:
    """Return `color` as `#rrggbb`, accepting a hex value or a name from `COLOR_HEX`."""
    if _HEX_RE.fullmatch(color):
        return color.lower()
    try:
        return COLOR_HEX[color.strip().lower()]
    except KeyError:
        raise ValueError(f"Team {team!r} has unknown color {color!r}.") from None


def load_roster(path: str | Path) -> Roster:
    """Read a `teams.toml` file into a `Roster`.

    Raises:
        ValueError: If a team is missing a name, abbreviation or color, or uses an unknown color.
    """
    with Path(path).open("rb") as f:
        data = tomllib.load(f)

    teams: list[Team] = []
    for entry in data.get("team", []):
        name = entry.get("name", "")
        missing = [k for k in ("name", "abbreviation", "colors") if not entry.get(k)]
        if missing:
            raise ValueError(f"Team {name!r} in {path} is missing: {', '.join(missing)}")
        teams.append(
            Team(
                name=name,
                abbreviation=entry["abbreviation"],
                url=entry.get("url", ""),
                colors=tuple(_color_to_hex(c, name) for c in entry["colors"]),
                aliases=tuple(entry.get("aliases", ())),
            )
        )
    return Roster(teams, schedule_url=data.get("schedule_url", ""), games_url=data.get("games_url", ""))