# p11-kit-server 0.26.2 W0 dependency report

Date: 2026-08-12

## Required dependency

| Reference | Reason | Local repository evidence | Registry evidence |
| --- | --- | --- | --- |
| `p11-kit/0.26.2` | Supplies `libp11-kit.so.0`; exact version includes the RPC security fix used by server 0.26.2 | PR #5125 is merged and its recipe is present on `main` | Shadow CI restored the previously verified binary cache; current CI L0 also resolves the dependency from `ohpcd` |

Optional upstream dependencies are disabled for this subpackage:

- libffi: disabled; upstream generates 64 fixed closures.
- libtasn1/asn1Parser: only needed for the trust module, which is disabled.
- systemd: socket activation units are disabled on OHOS.
- gettext, documentation, and shell completion tools: disabled.

## Decision

W0 is satisfied. Dependency PR #5125 has been merged, the branch is synchronized with `main`, and the latest Shadow CI L0 reports `dependency in registry: p11-kit/0.26.2`. The dependency adaptation remains isolated in issue 2074 and is not duplicated in issue 2072.

Earlier official CI builds stopped while computing the Conan dependency graph because the dependency was not yet merged and published:

```text
ERROR: Package 'p11-kit/0.26.2' not resolved: Unable to find 'p11-kit/0.26.2' in remotes.
```

Those logs are historical and no longer describe the current dependency state. The passing run at commit `b3ffa5b6c04e` completed Conan graph resolution, restored the exact dependency binary cache, built the package, ran 9/9 upstream tests, and completed test_package.

The CI R38 application-package check also expects software-level `commands.json`, while this round is restricted to the version directory. The current gate emits a warning rather than failing L0; no out-of-scope metadata is added by this branch.

The official CI pre-download log also prints truncated pseudo-URLs named `gh` and `p11` and reports that `curl` is absent. This comes from the infrastructure URL-extraction regular expression treating `-` as a terminator (`gh-proxy.com` and `p11-glue` are split); Conan still receives the complete rewritten URLs. It is not the fatal error in #21731/#21732 and cannot be fixed from this version-scoped PR.
