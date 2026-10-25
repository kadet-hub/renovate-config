# renovate-config

Renovate preset that updates Kapitan generators from
[kadet-hub](https://kadet-hub.org) in your Kapitan inventory.

```json
{
  "extends": ["github>kadet-hub/renovate-config"]
}
```

## Requirements

The preset updates sources in the tagged form the catalog shows:

```yaml
parameters:
  kapitan:
    dependencies:
      - type: oci
        source: ghcr.io/kadet-hub/<name>:<version>@sha256:<digest>
        output_path: lib/<name>
```

Pin the consumer workflow `kadet-hub/registry/.github/workflows/consumer.yml`
at `208fedc88f7b544b0614eeac3a96f221ac5ada2b`, the merge of
[kadet-hub/registry#234](https://github.com/kadet-hub/registry/pull/234), or
later. Older commits reject a tag in the source with `source must be
<host>/<repository>@sha256:<digest>`. Sources without a tag are not updated.

## What it does

A regex manager finds the source in `**/inventory/**/*.yml` and
`**/inventory/**/*.yaml`, so in an `inventory/` directory at the repository
root or in a nested Kapitan project. It looks up the generator's tags on
ghcr.io with the `docker` datasource and `semver` versioning. Each update is
its own pull request with the label `kadet-hub` and changes tag and digest
together. The preset sets `automerge: false` for these updates.

ghcr.io reports no release timestamps, so `minimumReleaseAge` cannot delay
generator updates. If your own configuration sets `minimumReleaseAge`,
Renovate 42 and later hold every update without a timestamp indefinitely;
the preset sets `minimumReleaseAgeBehaviour: timestamp-optional` for the
generator updates, so they still arrive, without a delay.

The consumer workflow checks every proposed version against the attested
index. Renovate reads only the tags, so it can propose a version that was
yanked after its release; the workflow then fails that pull request. Close
it: Renovate does not propose a closed version again, and a closed major
update skips that whole major line. See
[Using marketplace generators](https://github.com/kadet-hub/registry/blob/main/docs/consumers.md).

## Kubernetes versions

`kubernetes-versions.json` lists the three Kubernetes minors upstream
supports, each with the newest patch the latest kind release has a node image
for, the kind release itself and the kubeconform schema version. A daily
workflow recomputes it and opens a pull request when it changes. Format and
sources are defined in
[docs/specs/kubernetes-versions.md](docs/specs/kubernetes-versions.md).

```json
{
  "kind": {"version": "v0.33.0", "sha256": {"linux-amd64": "aee61515...", "linux-arm64": "20022bee..."}},
  "kubernetes": [
    {"minor": "1.37", "version": "1.37.0", "node_image": "kindest/node:v1.37.0@sha256:a1ed56cf...", "kubeconform": "1.37.0"},
    {"minor": "1.36", "version": "1.36.4", "node_image": "kindest/node:v1.36.4@sha256:099e0493...", "kubeconform": "1.36.4"},
    {"minor": "1.35", "version": "1.35.8", "node_image": "kindest/node:v1.35.8@sha256:07b2536e...", "kubeconform": "1.35.8"}
  ]
}
```

Fetch the file at a full commit SHA of this repository's `main`, replacing
`<commit>` below. With the preset in your Renovate config, Renovate moves
that SHA to the head of `main` in GitHub Actions workflows and `*.sh` files,
as a pull request labelled `kadet-hub`. Every merge here moves the head, so
that pull request can also come without a change to the list.

GitHub Actions matrix:

```yaml
name: kubernetes

on: pull_request

permissions: {}

defaults:
  run:
    shell: bash # with pipefail

jobs:
  kubernetes-versions:
    runs-on: ubuntu-24.04
    outputs:
      kind: ${{ steps.read.outputs.kind }}
      kubernetes: ${{ steps.read.outputs.kubernetes }}
    steps:
      - id: read
        run: |
          curl -fsSL https://raw.githubusercontent.com/kadet-hub/renovate-config/<commit>/kubernetes-versions.json \
            | jq -r '"kind=\(.kind | tojson)", "kubernetes=\(.kubernetes | tojson)"' >> "$GITHUB_OUTPUT"

  test:
    needs: kubernetes-versions
    runs-on: ubuntu-24.04
    name: kubernetes ${{ matrix.minor }}
    strategy:
      fail-fast: false
      matrix:
        include: ${{ fromJSON(needs.kubernetes-versions.outputs.kubernetes) }}
    env:
      KIND_VERSION: ${{ fromJSON(needs.kubernetes-versions.outputs.kind).version }}
      KIND_SHA256: ${{ fromJSON(needs.kubernetes-versions.outputs.kind).sha256.linux-amd64 }}
      NODE_IMAGE: ${{ matrix.node_image }}
      KUBECONFORM_VERSION: ${{ matrix.kubeconform }}
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - run: |
          curl -fsSLo "$RUNNER_TEMP/kind" "https://github.com/kubernetes-sigs/kind/releases/download/$KIND_VERSION/kind-linux-amd64"
          echo "$KIND_SHA256  $RUNNER_TEMP/kind" | sha256sum -c
          chmod +x "$RUNNER_TEMP/kind"
          "$RUNNER_TEMP/kind" create cluster --image "$NODE_IMAGE" --wait 120s
      - run: kubeconform -strict -kubernetes-version "$KUBECONFORM_VERSION" compiled/
```

Shell script, run in the checkout:

```bash
#!/usr/bin/env bash
set -euo pipefail
versions=$(curl -fsSL https://raw.githubusercontent.com/kadet-hub/renovate-config/<commit>/kubernetes-versions.json)
kind_version=$(jq -r .kind.version <<<"$versions")
kind version | grep -qF " $kind_version " || { echo "node images need kind $kind_version" >&2; exit 1; }
jq -r '.kubernetes[] | [.minor, .node_image, .kubeconform] | @tsv' <<<"$versions" |
  while IFS=$'\t' read -r minor node_image kubeconform_version; do
    kind create cluster --name "k8s-${minor/./-}" --image "$node_image" --wait 120s
    kubeconform -strict -kubernetes-version "$kubeconform_version" compiled/
    kind delete cluster --name "k8s-${minor/./-}"
  done
```

Both expect kubeconform on the `PATH`, the script also kind.

## Tests

The `test` workflow validates `default.json` and `renovate.json` with
`renovate-config-validator --strict`, then runs Renovate with
`--platform=local --dry-run=extract` and the preset over the fixtures in
`inventory/` and `platform/inventory/` and compares the extracted
dependencies with `test/expected.json`. The fixtures in `consumer/` are the
snippets above with a real SHA. `python3 -m unittest discover --start-directory test`
runs the unit tests for the `kubernetes-versions.json` computation.
