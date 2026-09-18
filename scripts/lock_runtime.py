"""Freeze the runtime dependency closure from the verified environment."""

import tomllib
from importlib.metadata import distribution
from pathlib import Path

from packaging.requirements import Requirement

project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
pending = [Requirement(value) for value in project["project"]["dependencies"]]
resolved = {}
visited = set()
while pending:
    requirement = pending.pop()
    if requirement.marker and not requirement.marker.evaluate():
        continue
    item = distribution(requirement.name)
    key = (item.metadata["Name"].lower(), tuple(sorted(requirement.extras)))
    if key in visited:
        continue
    visited.add(key)
    resolved[item.metadata["Name"]] = item.version
    for value in item.requires or []:
        dependency = Requirement(value)
        if not dependency.marker or any(
            dependency.marker.evaluate({"extra": extra}) for extra in (requirement.extras or {""})
        ):
            dependency.marker = None
            pending.append(dependency)
lines = [
    f"{name}=={version}"
    for name, version in sorted(resolved.items(), key=lambda item: item[0].lower())
]
if not any(line.lower().startswith("gunicorn==") for line in lines):
    lines += ['gunicorn==23.0.0; sys_platform != "win32"']
    if "packaging" not in {name.lower() for name in resolved}:
        lines += [f"packaging=={distribution('packaging').version}"]
Path("requirements-runtime.lock").write_text("\n".join(lines) + "\n", encoding="utf-8")
