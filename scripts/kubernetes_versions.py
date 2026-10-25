#!/usr/bin/env python3
"""Write kubernetes-versions.json, see docs/specs/kubernetes-versions.md."""

import json
import os
import re
import sys
import urllib.request

NODE_IMAGE = re.compile(r"kindest/node:v(\d+)\.(\d+)\.(\d+)@sha256:[0-9a-f]{64}")
KIND_ASSETS = {"linux-amd64": "kind-linux-amd64", "linux-arm64": "kind-linux-arm64"}
WINDOW = 3


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
    main(sys.argv[1])
