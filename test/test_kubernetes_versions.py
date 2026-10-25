import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from kubernetes_versions import compute  # noqa: E402

RELEASE = json.loads((ROOT / "test/kind-release-v0.33.0.json").read_text())
DIGEST = "0" * 64
SCHEMAS = {
    f"v{v}-{s}"
    for v in ("1.34.11", "1.35.8", "1.35.9", "1.36.4", "1.36.5", "1.37.0", "1.38.0")
    for s in ("standalone", "standalone-strict")
}


def release(body_edit=lambda b: b, tag="v0.34.0"):
    return dict(RELEASE, tag_name=tag, body=body_edit(RELEASE["body"]))


def window(result):
    return [k["version"] for k in result["kubernetes"]]


class Compute(unittest.TestCase):
    def test_kind_v0_33_0(self):
        result = compute("v1.37.1\n", RELEASE, SCHEMAS)
        self.assertEqual(window(result), ["1.37.0", "1.36.4", "1.35.8"])
        self.assertEqual(
            result["kubernetes"][2],
            {
                "minor": "1.35",
                "version": "1.35.8",
                "node_image": "kindest/node:v1.35.8@sha256:07b2536e30b803ed61d1677a79df6115f798ce64c80f9e22f6ed45afd09323c0",
                "kubeconform": "1.35.8",
            },
        )
        self.assertEqual(
            result["kind"],
            {
                "version": "v0.33.0",
                "sha256": {
                    "linux-amd64": "aee6151561422756b764a4ae28e7f44cda5af5a9eead3cc9985112b1de8d8e0d",
                    "linux-arm64": "20022bee6cfcd5086cb7234d218e3454e6090022f2a8f55d1fa7fcf42c3867a2",
                },
            },
        )

    def test_no_change(self):
        # A Kubernetes patch release without a new kind release changes nothing.
        self.assertEqual(compute("v1.37.2", RELEASE, SCHEMAS), compute("v1.37.1", RELEASE, SCHEMAS))

    def test_patch_bump(self):
        bumped = release(lambda b: b.replace("v1.36.4", "v1.36.5"))
        self.assertEqual(window(compute("v1.37.1", bumped, SCHEMAS)), ["1.37.0", "1.36.5", "1.35.8"])

    def test_new_minor_drops_the_oldest(self):
        new = release(lambda b: f"* v1.38.0: `kindest/node:v1.38.0@sha256:{DIGEST}`\n" + b)
        self.assertEqual(window(compute("v1.38.0", new, SCHEMAS)), ["1.38.0", "1.37.0", "1.36.4"])

    def test_new_minor_without_kind_image_keeps_the_window(self):
        self.assertEqual(compute("v1.38.0", RELEASE, SCHEMAS), compute("v1.37.1", RELEASE, SCHEMAS))

    def test_kind_two_minors_behind_fails(self):
        with self.assertRaises(ValueError):
            compute("v1.39.0", RELEASE, SCHEMAS)

    def test_missing_schema_fails(self):
        with self.assertRaises(ValueError):
            compute("v1.37.1", RELEASE, SCHEMAS - {"v1.36.4-standalone-strict"})

    def test_missing_kind_digest_fails(self):
        with self.assertRaises(ValueError):
            compute("v1.37.1", dict(RELEASE, assets=RELEASE["assets"][:1]), SCHEMAS)


class CommittedFile(unittest.TestCase):
    def test_schema(self):
        data = json.loads((ROOT / "kubernetes-versions.json").read_text())
        self.assertEqual(set(data), {"kind", "kubernetes"})
        self.assertRegex(data["kind"]["version"], r"^v\d+\.\d+\.\d+$")
        self.assertEqual(set(data["kind"]["sha256"]), {"linux-amd64", "linux-arm64"})
        for digest in data["kind"]["sha256"].values():
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
        self.assertEqual(len(data["kubernetes"]), 3)
        minors = []
        for k in data["kubernetes"]:
            self.assertEqual(set(k), {"minor", "version", "node_image", "kubeconform"})
            self.assertTrue(k["version"].startswith(k["minor"] + "."))
            self.assertRegex(k["node_image"], rf"^kindest/node:v{re.escape(k['version'])}@sha256:[0-9a-f]{{64}}$")
            self.assertEqual(k["kubeconform"], k["version"])
            minors.append(tuple(int(x) for x in k["minor"].split(".")))
        self.assertEqual(minors, sorted(set(minors), reverse=True))


if __name__ == "__main__":
    unittest.main()
