# Kubernetes versions to test against

Status: Draft
Code: `kubernetes-versions.json`, `scripts/kubernetes_versions.py`, `test/test_kubernetes_versions.py`, `test/kind-release-v0.33.0.json`, `.github/workflows/kubernetes-versions.yml`, `default.json` (KV-9), `consumer/`
Verified against: main @ fdd8595

## Problem

kadet-hub repositories should test generators and recipes against the
Kubernetes minors upstream supports. Each repository would otherwise pick its
own versions, node images and schema versions and update them by hand. Renovate
can bump a pinned version but cannot express "the three newest minors": it has
no rule that adds a matrix entry for a new minor and drops the oldest.

This repository therefore publishes one machine-readable list,
`kubernetes-versions.json`, that a scheduled workflow recomputes from primary
sources. Consumers fetch it at a renovate-config commit, and the preset lets
Renovate move that commit.

## File format

- KV-1: `kubernetes-versions.json` MUST be a JSON object with exactly the keys
  `kind` and `kubernetes`:

  ```json
  {
    "kind": {
      "version": "v0.33.0",
      "sha256": {
        "linux-amd64": "<64 hex>",
        "linux-arm64": "<64 hex>"
      }
    },
    "kubernetes": [
      {
        "minor": "1.37",
        "version": "1.37.0",
        "node_image": "kindest/node:v1.37.0@sha256:<64 hex>",
        "kubeconform": "1.37.0"
      }
    ]
  }
  ```

  `kubernetes` holds three entries, newest minor first, each with exactly
  these four keys. `version` is the patch release the node image was built
  from and starts with `minor`. `kubeconform` is the value for kubeconform's
  `-kubernetes-version` flag. `kind.version` is the kind release tag, and
  `kind.sha256` holds the SHA-256 of that release's `kind-linux-amd64` and
  `kind-linux-arm64` binaries.

  - Test: `test/test_kubernetes_versions.py` `CommittedFile.test_schema`
  - Since: this change

Node images are tied to the kind release that built them: kind's release
notes say the image must be used by digest with that release. So the file
carries the kind version and binary digests next to the images, and a
consumer installs exactly that kind.

## Which minors

Upstream maintains release branches for the three most recent minor
releases (Kubernetes version skew policy). The newest minor is the minor of
`https://dl.k8s.io/release/stable.txt`, the stable marker published by the
Kubernetes release team. The supported minors are that minor and the two
before it.

- KV-2: The window MUST be the three newest minors for which the latest kind
  release publishes a node image, ignoring minors newer than `stable.txt`.

  When kind already has an image for the newest stable minor, this is exactly
  the three upstream supported minors. When Kubernetes releases a minor before
  kind has an image for it, the window stays on the previous three until a
  kind release adds one; the oldest of them is then the minor upstream
  supported until that day.

  - Test: `test_kind_v0_33_0`, `test_new_minor_drops_the_oldest`,
    `test_new_minor_without_kind_image_keeps_the_window`, `test_no_change`
  - Since: this change

- KV-3: The computation MUST fail when the newest minor in the window is more
  than one minor behind `stable.txt`, or when fewer than three minors have a
  node image.

  A kind release that lags two minors would put a minor outside upstream
  support into the window. A failed scheduled run is visible in the Actions
  tab and leaves the file unchanged.

  - Test: `test_kind_two_minors_behind_fails`
  - Since: this change

- KV-4: Per minor, the entry MUST name the highest patch for which the latest
  kind release lists a `kindest/node:vX.Y.Z@sha256:<digest>` image, with the
  digest from those release notes.

  The latest release is GitHub's `releases/latest` of `kubernetes-sigs/kind`,
  which excludes drafts and pre-releases. The images are taken from the
  release body, the only place kind publishes the digests for a release.

  - Test: `test_kind_v0_33_0`, `test_patch_bump`
  - Since: this change

- KV-5: `kubeconform` MUST equal `version`, and the computation MUST fail
  unless `yannh/kubernetes-json-schema` has both `v<version>-standalone` and
  `v<version>-standalone-strict` at the top of its `master` branch.

  kubeconform's default schema location is that repository, and those are the
  directories it reads without and with `-strict`. The check uses the git tree
  API; the contents API truncates the listing at 1000 entries and the
  repository has more than 1100.

  - Test: `test_missing_schema_fails`
  - Since: this change

- KV-6: `kind.sha256` MUST come from the `digest` field GitHub reports for the
  release assets, and the computation MUST fail when one is missing.

  Verified for v0.33.0: the asset digests equal the release's
  `kind-linux-*.sha256sum` files.

  - Test: `test_missing_kind_digest_fails`, `test_kind_v0_33_0`
  - Since: this change

### DEC-1: stable.txt and the skew policy define "supported"

Upstream's own definition is the three most recent minors, and
`dl.k8s.io/release/stable.txt` names the newest one without parsing. No other
source is needed to derive the other two.

endoflife.date was considered. It is a third-party aggregation and lists
every minor before its end-of-life date, which today includes 1.34 (end of
life 2026-10-27) as a fourth minor. The release schedule in
`kubernetes/website` (`data/releases/schedule.yaml`) carries the same
end-of-life dates and would need YAML parsing for no gain over the policy.

### DEC-2: the window is computed from the inputs, not from the committed file

The computation reads only the three sources and does not look at the
current `kubernetes-versions.json`. Keeping the old window when kind lacks the
newest minor (KV-2) falls out of choosing among the minors kind has, so no
state is needed, and a run on any day reproduces the same file from the same
upstream state. A stateful rule ("keep the old minors until all three new
ones have images") would also freeze patch updates while kind lags.

### DEC-3: a stdlib Python script, not Renovate

Renovate could bump the digests of three fixed `kindest/node` entries, but
not add a minor and drop the oldest, and it cannot check that a schema
directory exists. A Python script with only the standard library runs on
the runner's system Python and needs no dependency pin.

## Update workflow

- KV-7: `.github/workflows/kubernetes-versions.yml` MUST run daily and on
  `workflow_dispatch`, recompute the file, and when it differs from `main`,
  commit it to the branch `update/kubernetes-versions` and open one pull
  request from that branch unless one is open.

  The job has `contents: write` and `pull-requests: write` and uses
  `GITHUB_TOKEN`. The checkout keeps no credentials; `gh auth setup-git` gives
  git the token only for the push. The workflow has no `pull_request_target`
  trigger and runs only code from `main`. The `main` ruleset requires a pull
  request, so the token cannot push to `main`.

  When the branch already holds the computed file, nothing is pushed, so an
  open pull request does not get a new commit every day. When the file
  changes again, the branch is reset onto `main` with one new commit.

  - Test: manual: `workflow_dispatch` run after merge (OQ-1)
  - Since: this change

Pull requests created with `GITHUB_TOKEN` do not trigger `pull_request`
workflows, so `test` does not run on them by itself (OQ-2).

## Consumers

A consumer fetches the file from `raw.githubusercontent.com` at a full
renovate-config commit SHA. The README has the snippets for a GitHub Actions
matrix and for a shell script; `consumer/` holds the same snippets as test
fixtures.

- KV-8: Consumers MUST fetch the file by commit SHA, never by branch.

  A branch URL would change the tested versions without a reviewed change in
  the consumer.

  - Test: none
  - Since: this change

- KV-9: The preset MUST update the commit SHA in
  `https://raw.githubusercontent.com/kadet-hub/renovate-config/<sha>/kubernetes-versions.json`
  in GitHub Actions workflows and `*.sh` files to the head of `main`, with the
  `git-refs` datasource, the label `kadet-hub`, no automerge and
  `minimumReleaseAgeBehaviour: timestamp-optional`.

  git-refs reports no timestamps. A Renovate 44.161.2 lookup with a consumer
  config that sets `minimumReleaseAge: "3 days"` and
  `minimumReleaseAgeBehaviour: timestamp-required` marked the digest update
  pending without the rule and proposed it with the rule.

  - Test: `test` workflow, extract of `consumer/` against `test/expected.json`
  - Since: this change

### DEC-4: pin to the head of main, not to tags

The repository has no tags, and a tag per data change would need a release
step in the update workflow. With `git-refs` on `main`, every merge to
`main` moves the SHA in consumers, also merges that do not touch the file.
That is one extra Renovate pull request per merge in each consumer, accepted
for now (OQ-3).

## Acceptance criteria

- AC-1: Given the kind v0.33.0 release and `stable.txt` v1.37.1, the
  computation yields 1.37.0, 1.36.4 and 1.35.8 with the digests from the
  release notes and the kind v0.33.0 binary digests. Checks KV-1, KV-2, KV-4,
  KV-6.
- AC-2: A new kind release with a new minor moves the window and drops the
  oldest minor; a new Kubernetes minor without a kind image changes nothing.
  Checks KV-2, KV-3.
- AC-3: The `test` workflow extracts the renovate-config SHA from both
  consumer snippets. Checks KV-9.

## Open questions

- OQ-1: The organisation and repository settings disallow GitHub Actions to
  create pull requests (`can_approve_pull_request_reviews: false`), so
  `gh pr create` in KV-7 fails with `GITHUB_TOKEN` after the push. The
  maintainer either enables "Allow GitHub Actions to create and approve pull
  requests" for the organisation and this repository, or the workflow uses a
  GitHub App token instead.
- OQ-2: `test` does not run on the update pull request (KV-7). Options are
  closing and reopening it by hand, a GitHub App token (whose pull requests
  do trigger workflows), or accepting it, since the unit tests run on `main`
  after the merge.
- OQ-3: Whether consumer pull requests for merges that do not touch the file
  (DEC-4) are too noisy, which would argue for tags.

## Implementation inventory

| Path | Role |
|---|---|
| `kubernetes-versions.json` | The list (KV-1) |
| `scripts/kubernetes_versions.py` | Computation (KV-2 to KV-6) and fetch of the three sources |
| `test/test_kubernetes_versions.py` | Unit tests and the committed file's schema check |
| `test/kind-release-v0.33.0.json` | Fixture: tag, body and linux asset digests of kind v0.33.0 |
| `.github/workflows/kubernetes-versions.yml` | Daily update and pull request (KV-7) |
| `.github/workflows/test.yml` | Runs the unit tests and the extract test |
| `default.json` | git-refs manager and packageRule (KV-9) |
| `consumer/` | README snippets as extract fixtures |
| Source: `https://dl.k8s.io/release/stable.txt` | Newest stable minor |
| Source: `https://api.github.com/repos/kubernetes-sigs/kind/releases/latest` | Node images, kind version and binary digests |
| Source: `https://api.github.com/repos/yannh/kubernetes-json-schema/git/trees/master` | kubeconform schema directories |
