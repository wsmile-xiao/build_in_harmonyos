# pex 1.20140409

HarmonyOS adaptation of the upstream `petere/pex` PostgreSQL package manager.

This package is a pure shell application. The Conan recipe installs:

- `bin/pex`
- `share/man/man1/pex.1`
- `share/doc/pex/README.md`
- `licenses/LICENSE`

The runtime still needs a POSIX shell, `curl`, and `git`. PostgreSQL tools
(`pg_config` and `psql`) are only needed by commands that manage PostgreSQL
extensions.

The upstream project has no C/C++ unit-test suite and no separately organized
integration-test suite. Its tests are 17 POSIX shell TAP files under `t/*.t`,
with 98 planned assertions when the optional Perl/YAML-backed `audit.t` suite
is available. The recipe runs `make check` on Linux and invokes the same
scripts explicitly through `/system/bin/sh` on OHOS.

The OHOS shadow CI runs #43625, #43670, #43815, #43866, and the current
branch-bound run #43900. The latest run #43900 passed Conan `test_package`,
the L0/L1 gates, and every build step on worker
`OpenHarmonyPCDeveloper-CI-020`. The recipe is a pure shell application, so
there is no native compilation step. The current evidence is 17 planned
upstream TAP files and 98 planned assertions; 16 files execute 88 assertions
in the CI image, with 10 `audit.t` assertions unavailable because Perl YAML is
not installed and one `pg_config.t` permission-precondition assertion
conditionally skipped because OHOS retained read mode bits after `chmod a-r`.
The remaining 87 executable assertions pass, and the separate Conan consumer
test has 15/15 assertions passing.

Earlier #43866 still failed at `pg_config.t` assertion 7 because its exported
recipe was the old mode-guard-only snapshot (`build()` line 79), not the
current `b795d9544c` recipe containing the conditional TAP boundary. It is
historical evidence only and must not override the authoritative #43900 result.
When the mode bits are actually removed, the original failure assertion
remains active and `pex` still has to return nonzero. The repository copy of
the upstream test files is unchanged.

Path B knowledge-draft candidates are included in the repository:

- `DRAFT-pex-1.20140409-ohos-shell-entrypoint` —
  纯 POSIX shell 应用在 OHOS 上需要同时修正测试入口与安装后 shebang
- `DRAFT-pex-1.20140409-tap-evidence-boundary` —
  pex 的上游测试必须按 shell TAP 真实入口统计，不能把单元测试和集成测试分类为 0/0 通过
- `DRAFT-pex-1.20140409-permission-semantics` —
  pex pg_config.t 的不可读 postmaster.opts 断言暴露 OHOS 与上游 POSIX 权限语义差异
- `DRAFT-pex-1.20140409-consumer-package-contract` —
  pex 的 Conan 消费者契约必须与上游 TAP 套件分开复核

They document the actual OHOS shell entrypoint boundary, the distinction
between test-category zeros and the real shell TAP suite, the observed
`pg_config.t` permission-semantic boundary, and the separate installed-package
consumer contract. They are application materials, not a claim that B-class
recognition has already been granted.
