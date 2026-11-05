# Preset for kadet-hub generators and recipes

Status: Draft
Code: `default.json` (PRE-1, PRE-2), `inventory/`, `platform/inventory/`, `fetch/`, `test/expected.json`, `.github/workflows/test.yml`
Verified against: main @ 8603833

## Problem

Consumers pin kadet-hub generators in their Kapitan inventory and kadet-hub
recipes in a separate fetch inventory, each as
`ghcr.io/kadet-hub/<path>:<version>@sha256:<digest>`. The registry's
consumer workflow verifies every pin against the attested index (CON-2 and
CON-5 in kadet-hub/registry). Renovate reads the tags on ghcr.io and not
the index, so the preset proposes updates and the workflow judges them.

A recipe can include other recipes, such as `immich`, which includes
`postgresql` and `valkey`. The consumer workflow takes those from the index
record of the recipe the fetch inventory pins (CON-7 there), so the fetch
inventory pins only the recipes the consumer's targets include. An update
of the `immich` pin therefore brings the `postgresql` and `valkey` that the
new `immich` record lists, and each pin can move in a pull request of its
own.

## Generators

- PRE-1: The preset MUST update tag and digest of a source
  `ghcr.io/kadet-hub/<name>:<version>@sha256:<digest>` in
  `**/inventory/**/*.yml` and `**/inventory/**/*.yaml` together, in one
  pull request per generator with the label `kadet-hub` and without
  automerge.

  ghcr.io reports no release timestamps, so the rule sets
  `minimumReleaseAgeBehaviour: timestamp-optional`. A source without a tag
  is not updated.

  - Test: workflow `test`, step "Extract the fixture inventory with the preset" (`inventory/targets/example.yml`, `platform/inventory/targets/cluster.yml` against `test/expected.json`)
  - Since: #1, #2

## Recipes

- PRE-2: The preset MUST update tag and digest of a source
  `ghcr.io/kadet-hub/recipes/<name>:<version>@sha256:<digest>` in
  `**/fetch/**/*.yml` and `**/fetch/**/*.yaml` together, in one pull
  request per recipe with the label `kadet-hub` and without automerge.

  `fetch` is the fetch inventory path that the registry's consumer guide,
  the recipe pages and the kadet-hub/recipes README use. A consumer whose
  policy names another path adds that path to the manager's
  `managerFilePatterns` in its own configuration. A recipe source in
  `inventory/` is not matched, because the consumer workflow refuses a
  recipe in the main inventory (CON-4 there).

  A fetch inventory written before the workflow added included recipes
  (CON-7) also pins them. The workflow accepts such a pin at the digest the
  parent's record lists (CON-9, DEC-45 there). Renovate updates it on its
  own, so its update and an update of the parent to a version that
  includes another digest fail until the consumer deletes the pin.

  - Test: workflow `test`, step "Extract the fixture inventory with the preset" (`fetch/targets/recipes.yml` pins `immich` only and extracts as one dependency; the recipe source in `inventory/targets/example.yml` extracts as none)
  - Since: #21
