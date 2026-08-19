# E2145 - Reconcile Downstream References After a Canonical Package Repair

## Symptom

A provider repair is merged and published under its canonical version, but a
downstream package still fails before compilation with an error such as:

```text
Unable to find '<provider>/<temporary-version>' in remotes
```

The downstream recipe may already be merged, and a similarly named provider
package is visibly available. Repeated CI runs do not help because the exact
reference requested by the downstream recipe does not exist.

## Root Cause

During provider recovery, a temporary suffixed version can be proposed to avoid
overwriting an earlier recipe. A later corrective change may instead replace
the broken provider recipe and retain the canonical upstream version. If the
temporary archive is removed, every downstream reference to it becomes stale.

Conan resolves exact references. A published canonical provider does not
satisfy a dependency on a removed suffix, even when both represent the same
upstream source release. This is a dependency contract defect, not a transient
network or build failure.

## Resolution

1. Use the merged provider recipe and formal remote binary retrieval as the
   authority for the exact version.
2. In a fresh isolated Conan home, run recipe download, graph inspection, and
   install with `--build=never` for the canonical reference.
3. Record the provider RREV, package ID, PREV, empty `info_invalid`, zero
   missing nodes, and the actual package folder.
4. Update the downstream `requirements()` reference and all package metadata
   that records the dependency graph.
5. Add a consumer-side graph contract that rejects the removed version, a
   missing dependency node, or a node without a binary package folder.
6. Rerun the downstream graph, complete upstream suite, consumer tests, and a
   current-snapshot target build.

## Negative Checks

The validation must reject all of these states:

- the obsolete reference remains in recipe or metadata;
- the provider node is absent from `self.dependencies`;
- the resolved version differs from the canonical version;
- `dependency.package_folder` is `None`;
- the graph needs `--build=missing` to succeed; or
- a local cache is used in place of formal remote retrieval.

Do not use `conan list` or `conan search` as binary proof. Do not upload a local
provider package from the downstream task.

## Verification Matrix

| Check | Required result |
|---|---|
| Provider recipe | Exact canonical reference downloads from the official remote |
| Provider graph | Empty `info_invalid`; zero missing nodes |
| Provider binary | RREV/PID/PREV and package folder retrieved with `--build=never` |
| Downstream recipe | Only the canonical provider reference remains |
| Consumer graph | Exact version and non-null binary folder enforced |
| Upstream suite | Complete registered suite passes N/N |
| Target run | Same current HEAD/tree snapshot builds and tests successfully |

## Source Evidence

Provider PR #4942 replaced the broken `librttopo/1.1.0` recipe and removed the
temporary `1.1.0.1` archive. The formal package therefore remained
`librttopo/1.1.0`. `libspatialite/5.1.0.1` was already merged with a dependency
on `librttopo/1.1.0.1`, so its release could not resolve the exact reference.

The downstream repair is published as the next package revision
`libspatialite/5.1.0.2`; it changed recipe and metadata to
`librttopo/1.1.0`, added an exact-version and binary-folder consumer contract, and passed a fresh
OHOS/arm64 target run with all 108 upstream tests, 17 consumer assertions, and
four dependency-contract negatives.

## Related Knowledge

E264 explains how to derive a signed legacy `*-config` executable from exact
Conan dependency metadata. It does not cover provider version replacement,
remote publication identity, or downstream reference reconciliation. This
entry addresses that separate dependency-release failure mode.
