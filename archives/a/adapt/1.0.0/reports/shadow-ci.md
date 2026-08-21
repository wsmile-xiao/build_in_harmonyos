# adapt 1.0.0 shadow CI report

## Result

- Date: 2026-08-19
- Device: HarmonyOS aarch64, `10.62.222.172:2222`
- Runner: `local-ohos-shadow-device1-adapt`
- Package: `archives/a/adapt/1.0.0`
- Frozen input SHA256: `05770528b24cf362ceb5c6bf2be2dfe594c4eae83f2d76e2e8fc5109e9d0ae92`
- Run root: `/storage/Users/currentUser/ohpc-ci-shadow/runs/05770528b24c-20260819T063629Z-adapt-25773`
- Status: PASS

## Gate summary

| Gate | Result | Detail |
|---|---|---|
| L0 | pass | all checks passed |
| L1 | pass | test_package executed |
| L2 | skip | pure Python library; no `bin/` directory |
| L4 | pass | no patches |
| L5 | pass | `lib/` contains packaged Python modules |

Build summary: `Total: 1`, `Success: 1`, `Failed: 0`.

## Functional evidence

The consumer test imported Adapt through the Conan-generated `VirtualRunEnv`,
registered vocabulary and an `IntentBuilder`, and resolved the utterance
`play the big bang theory`:

```text
adapt 1.0.0 intent determination: PASS
```

The L1e destructive check moved the packaged `lib/` directory away and
confirmed that `conan test` then failed. This proves the consumer test depends
on the packaged Adapt modules rather than a source-tree or ambient import.

## Reproducibility evidence

- Source SHA256: `a5e122ae27437b9dec932ff6470463bb734e909e45e02b672fc47afdeed2861c`
- Setup log SHA256: `f25436fb822cb80116a0409b3a8e8b0e1140e085206ade462edbd053fbedceb5`
- Build log SHA256: `9b34ef9d9f9d1159cbca8d684c5e3b29732f359b194bc93b29f76acb98e01802`
- Gate results SHA256: `6d9b8e0751ce62a741fc25e29c89b3526e779c19096458a327f878fe1d416447`

The device provided Python 3.12.9 and six 1.17.0. The `ohpcd` remote did not
contain a `six/*` recipe at test time, so six remains a separate dependency
adaptation/publication item and is not included in this change.

The generated `ci-metadata.json` retained the correct source SHA256 but showed
an empty source URL after the CI mirror fallback rewrote `conandata.yml` to a
URL list. The committed `conandata.yml` retains the canonical GitHub URL.
