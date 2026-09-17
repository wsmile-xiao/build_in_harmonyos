# GLib 2.88.3 adaptation notes

## Scope and status

This package adapts the official GLib 2.88.3 release for OpenHarmony PC
AArch64. The current candidate has a same-snapshot target W3 PASS and an
official finish build/test PASS. It is not a published package until the PR is
merged and the release pipeline publishes the exact recipe and binary.

Local P0/P1/P2/P3 scans and dual W4 are not current gates. Code findings are
handled by the platform AI Review after PR creation. Historical failed runs
remain immutable diagnostics and are excluded from the final denominators.

## Source and dependencies

- Source: `https://download.gnome.org/sources/glib/2.88/glib-2.88.3.tar.xz`
- SHA-256: `ab24d24e698dfa1e408b7bcdb508f4aafc906185a8b8ce72fdf79bbbdc9b383b`
- Build system: Meson, `wrap_mode=nofallback`, one build job, GPU disabled
- Exact providers: `pcre2/10.47`, `libffi/3.5.2`, `zlib/1.3.2`,
  `proxy-libintl/0.5`

Fresh W0 r859 resolved every provider as an OHOS/AArch64 binary from `ohpcd`
with `--build=never` and an empty `info_invalid` set. The recipe neither
vendors missing dependencies nor builds them from source.

## Adaptation summary

1. Journal peer-address support is selected from generated declaration and
   link capabilities. The unavailable branch retains a real implementation
   that reports unsupported behavior without a platform-name conditional.
2. Netlink monitoring is an explicit Meson feature because header presence
   alone does not establish the target runtime policy.
3. Visibility generators and interpreted test tools run through detected
   interpreters rather than direct shebang execution.
4. The source probes `proxy-libintl.pc` before Meson's special builtin/system
   `intl` factory, allowing Conan's external provider without fallback
   downloads.
5. Missing shared-library aliases are materialized as byte-identical regular
   files when the filesystem rejects symbolic links. The operation derives
   names from the actual versioned libraries, preserves mode, and validates
   the final SONAME/developer-name closure.
6. The `gio-launch-desktop` target declares the generated `config.h` include
   edge explicitly instead of relying on ambient include paths.
7. `getpass`, localtime, monotonic clock, filesystem links, optional tools,
   user database, locale formatting, socket behavior and other test-sensitive
   facilities use precise compile-link or runtime capability results.
8. The real consumer binds test-only `DT_RPATH`, rejects `DT_RUNPATH`, includes
   all required dependency libdirs, and executes against regular SONAME alias
   files. Absolute test paths are not packaged.

No source or patch conditional contains an OHOS-named macro. No upstream Meson
test registration is removed. Capability-limited internal branches retain the
outer test entry and bind the exact reason; unclassified failures continue to
use the upstream assertion path.

## Patch and test inventory

W2 r860 replayed all 19 patches against the official archive and passed the
directly related capability, package and consumer contracts. The source audit
found 372 literal test registrations and nine dynamic expressions; configured
Meson introspection is authoritative and produced 363 runnable outer entries.

The final target inventory is counted once:

- upstream Meson entries: 363/363 terminal success;
- internal composition: 359 OK plus four reason-bound capability SKIPs;
- package state test: 1/1;
- real Conan consumer program: 1/1;
- consumer assertions: 12/12 coverage metadata, not separate cases.

## Current W3 evidence

Run `glib-2.88.3-w3-transaction-r873` executed once on
`10.62.148.108:2222` with one build job and no GPU.

- source HEAD: `fdf98cd7a11119f65d90edae600c73d7ee0e94ee`
- source tree: `4d65f48243aeeffa9bd068e9c105b5f9d699fa82`
- runtime candidate: `66982ee9c8e9ec23baf33bb238bf7c0f6be0ce60`
- input SHA-256:
  `6830589cf8bd96d1e5d097485027521d1f03c33f43e9c0be41f7daaf9039b1de`
- result SHA-256:
  `b1847f14f65476dc8ac33575c8719db7e0e0850b274801f9b8dcbee6c5dad3d2`
- receipt head:
  `89d9c8878d4357fe883533c5d001657965d93a402d47cb851e231e532b2c847b`
- host result SHA-256:
  `3191f78de05253a334137b641f922cba9de66ca1fec3eefc1bfdc5c8290aa37b`
- lifecycle: 12 receipts, two clean scans, `POSTRELEASE_PASS`

The r872 predecessor remains unconsumed at launch count zero but has
unresolved historical cleanup evidence. Nothing in r873 reads, overwrites,
deletes or interprets that predecessor root.

## Official finish evidence

Official finish r876 used a parentless synthetic commit because a parented
bundle in the partial object store failed clone with missing parent objects.
The parentless bundle reproduced the exact candidate tree and protected input
hashes before target execution.

- synthetic commit: `466cc78e8c8daaf414efda4cbe95c6b5cc07033d`
- bundle SHA-256:
  `7e575ee7d9cbea221ea7c6154c37a7af3b47f47bdbe7d067dde5e3cb002aae4f`
- finish input SHA-256:
  `25b901299b3a2bf2a2c66fb5ee21830e12ec0e21c5bc97c61d56aafe7125ca00`
- `.ci-result.json` SHA-256:
  `fd857e0f93d25892e4b08b013e65b9b6f88dd55b85fa4a6aaf054e8baa54e000`
- local CI log SHA-256:
  `f812be937f460de1511ab945d9f2f3bfded0cb1d88075e52fec678182bcf19a3`

`setup.sh`, `build_and_test.sh`, and the generated result check passed. The
aggregate finish RC remains 1 because later repository-level steps reported
`PARTIAL_POST_W3`; this does not rewrite the official build/test substep as a
failure or the aggregate as a pass. The target root completed two clean scans.

## Reusable knowledge

The submitted E2173 draft records a cross-project generation-order failure:
after the main freeze rebind, a receiver or validator copied later can retain
predecessor helper bytes, SHA-256 or schema constants. Every late consumer must
bind the final helper tuple in its owning render block, require the current
tuple exactly once, reject the predecessor tuple, and be regenerated in a new
immutable freeze before one target transaction.

GLib r870 exposed a root-schema drift, r872 exposed a late receiver helper
identity drift, and r873 validated the corrected complete consumer closure on
target. The rule applies to generated device, CI and packaging pipelines and
does not authorize editing completed evidence or accepting multiple identities.

---

## 2.88.3.1 fix 轮次（r02, 2026-09-10）

在 main 既有 2.88.3 发布配方上的增量修复（R37 版本递增，原 2.88.3 目录与发布保持不变）：

1. gio-2.0.pc 恢复 `gdbus_codegen` 变量：gio 组件 `pkg_config_custom_content={'gdbus_codegen': '${bindir}/gdbus-codegen'}`，
   修复 meson 消费方 `dependency('gio-2.0').get_variable('gdbus_codegen')` 首错
   `Could not get pkg-config variable and no default provided for gio-2.0`。
2. gdbus-codegen python 脚本随包安装至 `bin/`（`#!/usr/bin/env python3`）并可执行。
3. 版本递增 2.88.3 → 2.88.3.1（conanfile.py version、manifest.yaml version/conan_ref、顶层 manifest versions、commands.json versions）。
4. 下游引用核验：cataract/1.0.0、gnome-autoar/0.5.2、libvips/8.18.4 仍引用已发布 glib/2.88.3（main 既有版本保持有效，不强制升级；需 gdbus 修复的下游由各自 follow-up 切换 2.88.3.1），与 dbus/1.14.10.1 fix 轮次同型（fix 只改本库目录）。
