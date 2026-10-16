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

## Tests

The `test` workflow validates `default.json` and `renovate.json` with
`renovate-config-validator --strict`, then runs Renovate with
`--platform=local --dry-run=extract` and the preset over the fixtures in
`inventory/` and `platform/inventory/` and compares the extracted
dependencies with `test/expected.json`.
