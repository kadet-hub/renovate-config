#!/usr/bin/env bash
set -euo pipefail
url=https://raw.githubusercontent.com/kadet-hub/renovate-config/fdd859537fcd6a16e036e4f6aa4557e5d5fb1a54/kubernetes-versions.json # kubernetes-versions-2026-10-25
versions=$(curl -fsSL "$url")
kind_version=$(jq -r .kind.version <<<"$versions")
kind version | grep -qF " $kind_version " || { echo "node images need kind $kind_version" >&2; exit 1; }
jq -r '.kubernetes[] | [.minor, .node_image, .kubeconform] | @tsv' <<<"$versions" |
  while IFS=$'\t' read -r minor node_image kubeconform_version; do
    kind create cluster --name "k8s-${minor/./-}" --image "$node_image" --wait 120s
    kubeconform -strict -kubernetes-version "$kubeconform_version" compiled/
    kind delete cluster --name "k8s-${minor/./-}"
  done
