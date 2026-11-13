#!/usr/bin/env python3
"""Lint the skill library: bodies, versions, section references and model names.

Usage: python scripts/lint.py [root]

Prints one line per problem, `<path>:<line>: [<check>] <message>`, and exits 1 when there
is any problem; otherwise prints `lint: ok`. Standard library only.
"""

import json
import re
import sys
from pathlib import Path

# A problem is (posix path relative to root, line, check, message).


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def read(root, path, check, out):
    """Return the UTF-8 text of `path`, or None after recording a problem."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        out.append((rel(root, path), 1, check, "cannot read file: %s" % exc))
        return None


def rel(root, path):
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def frontmatter_end(lines):
    """Index of the closing `---` line of the frontmatter, or -1 when there is none."""
    if not lines or lines[0].strip() != "---":
        return -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return i
    return -1


def frontmatter(lines):
    """Plain `key: value` lines of the frontmatter."""
    end = frontmatter_end(lines)
    fields = {}
    for line in lines[1:end] if end > 0 else []:
        key, sep, value = line.partition(":")
        if sep and key.strip() and not key.startswith((" ", "\t")):
            fields[key.strip()] = value.strip()
    return fields


def plugin_dirs(root):
    return sorted(p for p in (root / "plugins").glob("*") if p.is_dir())


# --- 1. identical implementer bodies -------------------------------------------------


def check_bodies(root):
    out = []
    for plugin in plugin_dirs(root):
        files = sorted((plugin / "agents").glob("*-implementer-*.md"))
        bodies = []
        for path in files:
            text = read(root, path, "bodies", out)
            if text is None:
                continue
            lines = text.split("\n")
            end = frontmatter_end(lines)
            if end < 0:
                out.append((rel(root, path), 1, "bodies", "no YAML frontmatter"))
                continue
            bodies.append((path, end + 1, lines[end + 1 :]))
        for path, offset, body in bodies[1:]:
            first_path, _, first = bodies[0]
            for i in range(max(len(first), len(body))):
                a = first[i] if i < len(first) else None
                b = body[i] if i < len(body) else None
                if a != b:
                    out.append(
                        (
                            rel(root, path),
                            offset + min(i, len(body)) + 1,
                            "bodies",
                            "body differs from %s at its line %d"
                            % (first_path.name, bodies[0][1] + min(i, len(first)) + 1),
                        )
                    )
                    break
    return out


# --- 2. marketplace and plugin versions ----------------------------------------------


def load_json(root, path, check, out):
    text = read(root, path, check, out)
    if text is None:
        return None, ""
    try:
        return json.loads(text), text
    except ValueError as exc:
        out.append((rel(root, path), 1, check, "malformed JSON: %s" % exc))
        return None, text


def check_versions(root):
    out = []
    market = root / ".claude-plugin" / "marketplace.json"
    mrel = rel(root, market)
    data, text = load_json(root, market, "versions", out)
    listed = set()
    entries = data.get("plugins") if isinstance(data, dict) else None
    if data is not None and not isinstance(entries, list):
        out.append((mrel, 1, "versions", "`plugins` is missing or not a list"))
        entries = []
    start = max(text.find('"plugins"'), 0)
    for entry in entries or []:
        if not isinstance(entry, dict):
            out.append((mrel, 1, "versions", "plugin entry is not an object"))
            continue
        name = entry.get("name")
        at = 1
        if isinstance(name, str):
            found = text.find(json.dumps(name), start)
            at = line_of(text, found) if found >= 0 else 1
        source = entry.get("source")
        manifest = None
        if isinstance(source, str):
            manifest = root / source / ".claude-plugin" / "plugin.json"
            listed.add(manifest.resolve())
        missing = [k for k in ("name", "source", "version") if not isinstance(entry.get(k), str)]
        if missing:
            out.append((mrel, at, "versions", "entry lacks %s" % ", ".join(missing)))
            continue
        if not manifest.is_file():
            out.append((mrel, at, "versions", "%s does not exist" % rel(root, manifest)))
            continue
        info, _ = load_json(root, manifest, "versions", out)
        if info is None:
            continue
        if not isinstance(info, dict):
            out.append((rel(root, manifest), 1, "versions", "plugin.json is not an object"))
            continue
        for key in ("name", "version"):
            if info.get(key) != entry[key]:
                out.append(
                    (
                        mrel,
                        at,
                        "versions",
                        "%s %r differs from %s %r"
                        % (key, entry[key], rel(root, manifest), info.get(key)),
                    )
                )
    if data is not None:
        for manifest in sorted((root / "plugins").glob("*/.claude-plugin/plugin.json")):
            if manifest.resolve() not in listed:
                out.append(
                    (rel(root, manifest), 1, "versions", "plugin is not listed in marketplace.json")
                )
    return out


# --- 3. section references (convention C1) -------------------------------------------

MASTER = re.compile(
    r"""
      (?P<its>\b[Ii]ts\s+§(?:\d+)?)
    | `(?P<name>[^`\n]+)`(?:['’]s)?\s+§(?P<nsec>\d+)
    | \bSKILL\.md\s+§(?P<ssec>\d+)
    | §(?P<bsec>\d+)
    """,
    re.VERBOSE,
)
CHAIN = re.compile(
    r"(?:\s+(?:steps?|triggers?)\s+\d+(?:[–-]\d+)?(?:\s+and\s+\d+)?)?(?:,\s+|\s+and\s+)§(\d+)"
)
HEADING = re.compile(r"^## (\d+)\. ", re.MULTILINE)


def skill_sections(root):
    """Map skill name -> set of section numbers, over all plugins."""
    skills = {}
    for skill_md in sorted((root / "plugins").glob("*/skills/*/SKILL.md")):
        try:
            text = skill_md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            text = ""  # reported by check_refs when it reads the file
        skills.setdefault(skill_md.parent.name, set()).update(
            int(n) for n in HEADING.findall(text)
        )
    return skills


def check_refs(root):
    out = []
    skills = skill_sections(root)
    files = sorted((root / "plugins").glob("*/skills/*/*.md")) + sorted(
        (root / "plugins").glob("*/agents/*.md")
    )
    for path in files:
        text = read(root, path, "refs", out)
        if text is None:
            continue
        in_skill = path.parent.parent.name == "skills"
        own = path.parent.name if in_skill else None
        p = rel(root, path)

        def problem(pos, message):
            out.append((p, line_of(text, pos), "refs", message))

        def section_problems(skill, sections, positions):
            for n, pos in positions:
                if n not in sections:
                    problem(pos, "`%s` has no section §%d" % (skill, n))

        pos = 0
        while True:
            m = MASTER.search(text, pos)
            if not m:
                break
            kind = "its" if m.group("its") else (
                "name" if m.group("name") else ("ssec" if m.group("ssec") else "bsec")
            )
            sign = text.index("§", m.start(), m.end())
            num = m.group("nsec") or m.group("ssec") or m.group("bsec")
            positions = [(int(num), sign)] if num else []
            end = m.end()
            # a bare reference does not chain: its neighbours are matched on their own
            while kind != "bsec":
                c = CHAIN.match(text, end)
                if not c:
                    break
                positions.append((int(c.group(1)), c.start(1) - 1))
                end = c.end()
            pos = end

            if kind == "its":
                problem(sign, "ambiguous reference: name the skill")
            elif kind == "name" and m.group("name") != "SKILL.md":
                name = m.group("name")
                if name not in skills:
                    problem(sign, "unknown skill `%s`" % name)
                else:
                    section_problems(name, skills[name], positions)
            elif own is None and kind == "bsec":
                problem(sign, "name the skill: a bare §N has no skill in an agent file")
            elif own is None:
                problem(sign, "no SKILL.md beside this file: name the skill")
            else:  # bare §N, SKILL.md §N or `SKILL.md` §N: this directory's skill
                section_problems(own, skills.get(own, set()), positions)
    return out


# --- 4. model names and tiers --------------------------------------------------------


def agents_of(root, plugin, out):
    """Agents of one plugin as dicts with path, name, model, effort, short, label."""
    agents = []
    for path in sorted((plugin / "agents").glob("*.md")):
        text = read(root, path, "models", out)
        if text is None:
            continue
        fields = frontmatter(text.split("\n"))
        missing = [k for k in ("name", "model", "effort") if not fields.get(k)]
        if missing:
            out.append((rel(root, path), 1, "models", "frontmatter lacks %s" % ", ".join(missing)))
            continue
        short = fields["model"]
        short = short[len("claude-") :] if short.startswith("claude-") else short
        agents.append(
            dict(
                path=path,
                name=fields["name"],
                model=fields["model"],
                effort=fields["effort"],
                short=short,
                label="%s:%s" % (short, fields["effort"]),
            )
        )
    return agents


def table_rows(text):
    return [(i, l) for i, l in enumerate(text.split("\n"), 1) if l.lstrip().startswith("|")]


def check_agent_rows(agents, rows, check_path):
    """Every row naming an agent must carry its label."""
    out = []
    for i, row in rows:
        for a in agents:
            if "`%s`" % a["name"] in row and "`%s`" % a["label"] not in row:
                out.append(
                    (check_path, i, "models", "row names `%s` without `%s`" % (a["name"], a["label"]))
                )
    return out


def check_models(root):
    out = []
    all_agents = []
    for plugin in plugin_dirs(root):
        agents = agents_of(root, plugin, out)
        all_agents += agents
        if not agents:
            continue
        seen = set()
        for skill_md in sorted(plugin.glob("skills/*/SKILL.md")):
            text = read(root, skill_md, "models", out)
            if text is None:
                continue
            rows = table_rows(text)
            out += check_agent_rows(agents, rows, rel(root, skill_md))
            for _, row in rows:
                seen.update(a["name"] for a in agents if "`%s`" % a["name"] in row)
        for a in agents:
            if a["name"] not in seen:
                out.append(
                    (rel(root, a["path"]), 1, "models", "no SKILL.md table row names `%s`" % a["name"])
                )

    shorts = sorted({a["short"] for a in all_agents})
    names = [a["name"] for a in all_agents]
    for path in sorted((root / "plugins").rglob("*.md")):
        text = read(root, path, "models", out)
        if text is None:
            continue
        lines = text.split("\n")
        in_agents = path.parent.name == "agents" and path.parent.parent.parent.name == "plugins"
        fm_end = frontmatter_end(lines) if in_agents else -1
        for i, line in enumerate(lines):
            if i <= fm_end or not any(s in line for s in shorts):
                continue
            if (
                path.name == "SKILL.md"
                and line.lstrip().startswith("|")
                and any("`%s`" % n in line for n in names)
            ):
                continue
            out.append(
                (rel(root, path), i + 1, "models", "model id outside the agent table: name the tier")
            )

    readme = root / "README.md"
    if readme.is_file() and all_agents:
        text = read(root, readme, "models", out)
        if text is not None:
            out += check_agent_rows(all_agents, table_rows(text), "README.md")
            out += check_routing(text, all_agents)
    return out


def check_routing(text, agents):
    out = []
    comment = r"(?:[ \t]+#.*)?[ \t]*$"
    roles = re.search(r"^[ \t]*modelRoles:[ \t]*$", text, re.M)
    for a in agents:
        route = re.search(
            r'^[ \t]*%s:[ \t]*"@([\w-]+)"%s' % (re.escape(a["name"]), comment), text, re.M
        )
        if not route:
            out.append(("README.md", 1, "models", "no oh-my-pi routing line `%s: \"@<role>\"`" % a["name"]))
            continue
        at = line_of(text, route.start())
        if not roles:
            out.append(("README.md", at, "models", "README has no `modelRoles:` snippet"))
            continue
        role = route.group(1)
        role_line = re.compile(r"^[ \t]*%s:[ \t]*(\S+)%s" % (re.escape(role), comment), re.M).search(
            text, roles.end()
        )
        want = "/%s:%s" % (a["model"], a["effort"])
        if not role_line:
            out.append(("README.md", at, "models", "role `%s` has no model line" % role))
        elif not role_line.group(1).endswith(want):
            out.append(
                (
                    "README.md",
                    line_of(text, role_line.start()),
                    "models",
                    "role `%s` is %s, but `%s` needs ...%s" % (role, role_line.group(1), a["name"], want),
                )
            )
    return out


# --- main ----------------------------------------------------------------------------


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent
    root = root.resolve()
    problems = []
    for check in (check_bodies, check_versions, check_refs, check_models):
        problems += check(root)
    problems = sorted(set(problems))
    for path, line, check, message in problems:
        print("%s:%d: [%s] %s" % (path, line, check, message))
    if not problems:
        print("lint: ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
