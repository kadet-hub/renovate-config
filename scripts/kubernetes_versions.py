#!/usr/bin/env python3
"""Write kubernetes-versions.json, see docs/specs/kubernetes-versions.md."""

import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

NODE_IMAGE = re.compile(r"kindest/node:v(\d+)\.(\d+)\.(\d+)@sha256:[0-9a-f]{64}")
KIND_ASSETS = {"linux-amd64": "kind-linux-amd64", "linux-arm64": "kind-linux-arm64"}
WINDOW = 3
TAG_PREFIX = "kubernetes-versions-"
TAG = re.compile(TAG_PREFIX + r"(\d{4}-\d{2}-\d{2})(?:-(\d+))?")


def compute(stable, release, schema_dirs):
    """stable: dl.k8s.io stable.txt, release: kind GitHub release, schema_dirs: yannh tree."""
    stable_minor = tuple(int(x) for x in stable.strip().lstrip("v").split(".")[:2])

    newest = {}
    for m in NODE_IMAGE.finditer(release["body"]):
        major, minor, patch = (int(x) for x in m.groups())
        if (major, minor) <= stable_minor and patch >= newest.get((major, minor), (-1, ""))[0]:
            newest[(major, minor)] = (patch, m.group(0))

    minors = sorted(newest, reverse=True)[:WINDOW]
    if len(minors) < WINDOW or minors[0] < (stable_minor[0], stable_minor[1] - 1):
        raise ValueError(f"kind {release['tag_name']} has node images for {minors}, stable is {stable.strip()}")

    kubernetes = []
    for major, minor in minors:
        patch, image = newest[(major, minor)]
        version = f"{major}.{minor}.{patch}"
        for suffix in ("standalone", "standalone-strict"):
            if f"v{version}-{suffix}" not in schema_dirs:
                raise ValueError(f"no kubeconform schema v{version}-{suffix}")
        kubernetes.append({"minor": f"{major}.{minor}", "version": version, "node_image": image, "kubeconform": version})

    digests = {a["name"]: a.get("digest") or "" for a in release["assets"]}
    sha256 = {}
    for platform, name in KIND_ASSETS.items():
        if not digests.get(name, "").startswith("sha256:"):
            raise ValueError(f"kind {release['tag_name']} has no sha256 digest for {name}")
        sha256[platform] = digests[name].removeprefix("sha256:")

    return {"kind": {"version": release["tag_name"], "sha256": sha256}, "kubernetes": kubernetes}


def next_tag(changed, date, tags, head_tags):
    """Tag for the pushed head, or None when the list did not change or the head is tagged."""
    if not changed or any(t.startswith(TAG_PREFIX) for t in head_tags):
        return None
    tag = f"{TAG_PREFIX}{date}"
    n = 2
    while tag in tags:
        tag = f"{TAG_PREFIX}{date}-{n}"
        n += 1
    return tag


def newest_tag(tags):
    """The tag Renovate's regex versioning sorts last (KV-9), or None."""
    keyed = [(m[1], int(m[2] or 1), t) for t in tags if (m := TAG.fullmatch(t))]
    return max(keyed)[2] if keyed else None


def tag(after):
    git = lambda *a: subprocess.run(["git", *a], capture_output=True, text=True)
    tags = git("tag", "--list", TAG_PREFIX + "*").stdout.split()
    newest = newest_tag(tags)
    changed = True
    if newest:
        diff = git("diff", "--quiet", newest, after, "--", "kubernetes-versions.json")
        if diff.returncode not in (0, 1):
            raise RuntimeError(diff.stderr)
        changed = diff.returncode == 1
    head_tags = git("tag", "--points-at", after).stdout.split()
    print(next_tag(changed, datetime.now(timezone.utc).date().isoformat(), set(tags), head_tags) or "")


def fetch(url, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return r.read().decode()


def main(path):
    token = os.environ.get("GH_TOKEN")
    stable = fetch("https://dl.k8s.io/release/stable.txt")
    release = json.loads(fetch("https://api.github.com/repos/kubernetes-sigs/kind/releases/latest", token))
    tree = json.loads(fetch("https://api.github.com/repos/yannh/kubernetes-json-schema/git/trees/master", token))
    if tree["truncated"]:
        raise ValueError("yannh/kubernetes-json-schema tree listing is truncated")
    result = compute(stable, release, {e["path"] for e in tree["tree"]})
    with open(path, "w") as f:
        f.write(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    if sys.argv[1] == "tag":
        tag(sys.argv[2])
    else:
        main(sys.argv[1])
