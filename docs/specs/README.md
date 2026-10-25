# Specs

One living spec per area in `docs/specs/<area>.md`. A change to the preset,
the data files or CI starts by editing the spec it touches, in the same pull
request, as its first commit.

Header of every spec:

```
Status: Draft | Approved | As-built | Superseded by <file>
Code: <paths this spec governs>
Verified against: main @ <commit>
```

The body opens with the problem and the decisions, closes with open questions
and the implementation inventory, and is organised by technical subject in
between. Requirements carry an area prefix (`KV-3`), are never renumbered or
reused, and name their check and origin:

```markdown
- KV-3: The computation MUST fail when kind lags two minors behind.

  - Test: <test function, CI job or `manual:` runbook step> | none
  - Since: <PR or commit> | this change | not implemented
```

Decisions are `DEC-n`, open questions `OQ-n`, acceptance criteria `AC-n`;
every acceptance criterion names the requirements it checks.

| Spec | Area |
|---|---|
| [kubernetes-versions.md](kubernetes-versions.md) | `kubernetes-versions.json`, its update workflow and how consumers pin it |
