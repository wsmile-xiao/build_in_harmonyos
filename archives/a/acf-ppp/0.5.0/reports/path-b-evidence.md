# acf-ppp 0.5.0 Path B evidence

## Application boundary

This report supports a Path B reusable-knowledge request for `acf-ppp/0.5.0`
under issue `#211`. Path A remains the library adaptation. Path B is limited to
the generalized package-graph method documented in the accompanying E321 draft;
the committee determines whether it is sufficiently novel and reusable.

## Observed failure

The official source contains four view links whose targets live in `acf-core`,
not in the standalone `acf-ppp` archive. They are deliberately dangling before
the ACF packages are overlaid:

| Source entry | Deployment target |
|---|---|
| `ppp-editchap-html.lsp` | `../filedetails-html.lsp` |
| `ppp-editpap-html.lsp` | `../filedetails-html.lsp` |
| `ppp-editpeer-html.lsp` | `../filedetails-html.lsp` |
| `ppp-status-html.lsp` | `../status-html.lsp` |

HarmonyOS extraction omitted the dangling entries, while direct `symlink()` on
the HMDFS build path raised `PermissionError`. The unguarded build therefore
could succeed with four required runtime views absent.

## Existing-knowledge comparison

| Entry | Existing scope | Gap addressed by this candidate |
|---|---|---|
| E018 | Generic symlink creation failure; wrapper or copy fallback | Does not resolve a target owned by a different package or bind the copy to a declared dependency version |
| E050 | Same-package shared-library alias copied from its real `.so` | Assumes alias and target are installed together; no cross-package ownership or containment contract |
| E073 | Runtime loader failure through shared-library symlinks | Focuses ELF loader/SONAME behavior rather than immutable application resources assembled from a Conan graph |

The candidate reuses the HMDFS premise. Its proposed addition is the complete
cross-package contract: dependency ownership, explicit mapping, path
containment, deterministic materialization, byte identity and representation
checks tied to the dependency selected by Conan.

## Reusable algorithm

Inputs:

1. a declared Conan runtime dependency;
2. a dependency-relative root containing immutable regular resources;
3. a package-relative destination root; and
4. an explicit destination-to-source mapping.

Required behavior:

1. Resolve the dependency root and each source with `realpath`.
2. Enforce source containment within the dependency root.
3. Enforce lexical destination and resolved parent containment within the
   package root.
4. Reject missing, non-regular or linked source resources.
5. Remove an existing destination with `lexists` before `copy2`, because
   `copy2` follows a destination symlink.
6. Copy metadata and content into a regular file.
7. Fail packaging unless the destination is regular, non-link and byte-equal to
   the dependency source.

Outputs:

- self-contained regular resource files in the consumer package;
- no dependency on HMDFS link creation or deployment-time link resolution; and
- deterministic content selected by the Conan dependency graph.

## Forbidden scope

Do not use this method for executables that need wrapper semantics, mutable
configuration, sockets/devices, large datasets, security identity files, or an
application that observes link identity. Do not copy from undeclared system
paths or maintain a second golden copy in the recipe. Those cases need a
deployment overlay, wrapper, platform filesystem change or explicit data
ownership redesign.

## Verification contract

Each mapping needs both content and representation checks:

```sh
cmp -s "$packaged_resource" "$resolved_dependency_resource"
test -f "$packaged_resource"
test ! -L "$packaged_resource"
```

For `acf-ppp`, the consumer test contains four byte comparisons, four
regular-file checks and four non-link checks. Nine Lua checks then execute the
packaged model and controller with isolated ACF stubs. Together with six base
files and the Lua runner check, the total is 28 independent assertions.

## Validation evidence

The updated candidate passed single-package HarmonyOS shadow CI at snapshot
`3233ff08e867357d49bbab3ef55a6682ac500f49`. The build summary was 1/1,
the consumer result was 28/28, and the Lua runner reported 9 functional
checks. L0, L1 and L4 passed; L2 was not applicable because the package has no
CLI; L5 emitted the expected warning because this pure resource application has
no `bin/` or `lib/` directory.

The isolated inner run is
`/storage/Users/currentUser/ohpc-ci-shadow/runs/3233ff08e867-20260813T112828Z-run-29337`,
completed at `2026-08-13T11:28:59Z`. Its Conan home was new and populated only
from checksum-verified dependency cache archives before building `acf-ppp`.

This proves the Path B implementation before dependency publication. Dependency
PR `#5226` has since merged and its successful release pipeline published
`ppp/2.5.2`. Implementation commit `24ebcc862a` subsequently passed the complete
official acf-ppp pipeline as CI `#26382`, satisfying formal W0.

Reproduction command:

```sh
CI_PACKAGES="archives/a/acf-ppp/0.5.0" zsh ci/conan/build_and_test.sh
```

The runtime boundary remains unchanged: this verifies packaging and
non-privileged Lua behavior, not a live PPP/PPPoE link.
