# fluent-bit 5.0.9 Upstream Test Non-execution Reasons

Date: 2026-08-18 +0800

This is the review-facing reason matrix for upstream tests that are not part of
the current OpenHarmony supported CTest claim. It supersedes the older 79/81
inventory language in historical follow-up notes, while keeping those notes as
evidence for how each boundary was found.

## Current Claim

- Current supported OHOS CTest route: `r170-full-supported-ctest`.
- Result: 177/177 CTests passed on device.
- Runtime: CTest 2294 seconds, total task 2303 seconds.
- Label totals from r170: 95 runtime CTests and 82 internal CTests.
- Package smoke remains separate package validation and is not counted as
  upstream CTest coverage.
- Raw upstream full surface is not claimed as passed.

There is no unclassified catch-all bucket in the final PR accounting. Every
upstream item outside the counted 177-test route is assigned to one of the
reason categories below.

## Reason Categories

| Category | Meaning |
|---|---|
| `not_registered_build_matrix` | The upstream test is behind a CMake feature/plugin/dependency gate that is outside the current OHOS supported recipe matrix. |
| `source_level_platform_boundary` | The original upstream test path depends on Linux/glibc/socket behavior that is not available with the observed OHOS device semantics. |
| `source_level_environment_stability` | The original upstream subcase was removed from the supported route after ordered or repeated OHOS runs showed timing-sensitive crashes, stale-state sensitivity, or unstable filesystem watcher behavior. |
| `external_service_or_token_gate` | The test depends on an external service, credential, token, or service-side retry path that is not suitable for package CI. |
| `separate_integration_harness` | The test belongs to the pytest/integration harness rather than the CTest route used by this Conan package PR. |
| `historical_audit_boundary` | The target was part of a historical exploration route and is preserved as evidence, but it is not counted unless it is registered and passed in the final supported route. |

## Non-executed / Adjusted Surface Matrix

| Upstream surface | Current OHOS handling | Reason category | Evidence / rationale |
|---|---|---|---|
| CTests registered in `r170-full-supported-ctest` | Executed and counted | passed supported route | r170 passed 177/177 with 95 runtime and 82 internal CTests. |
| Full raw plugin/feature matrix beyond the r170 supported recipe gates | Not registered and not counted | `not_registered_build_matrix` | Fluent Bit registers CTests through CMake feature and plugin gates. The recipe does not turn every `FLB_IN_*`, `FLB_OUT_*`, `FLB_FILTER_*`, and processor option on at once; r5 broad expansion already showed link pressure through static OpenSSL AArch64 relocation overflow. |
| Generated parser/toolchain surfaces: record accessor, stream processor, processor SQL/template family | Not registered and not counted | `not_registered_build_matrix` | These are gated by generated parser/toolchain requirements such as usable Flex/Bison or pre-generated sources. `FLB_RECORD_ACCESSOR`, `FLB_STREAM_PROCESSOR`, and `FLB_PROCESSOR_SQL` remain outside the supported matrix. |
| Service-heavy or OS-specific inputs such as systemd, kmsg, proc, podman/docker events, Kubernetes events, Windows inputs, and Unix socket input | Not registered and not counted | `not_registered_build_matrix` / `source_level_platform_boundary` | These families depend on host services, kernel interfaces, or OS-specific facilities not present in the OHOS package CI environment. |
| Service-heavy outputs such as Azure Logs Ingestion, BigQuery, GELF, NATS, Oracle, PostgreSQL, Prometheus exporter/remote write, Slack, Stackdriver, UDP output, Vivo exporter, and websocket | Not registered and not counted | `not_registered_build_matrix` / `external_service_or_token_gate` | They require service credentials, external endpoints, or plugin families outside the supported package matrix. |
| `tests/integration` tree | Not counted in upstream CTest claim | `separate_integration_harness` | The integration tree uses pytest scenarios, external ports/services, and a separate harness; the PR claim is scoped to the Conan package CTest route. |
| Runtime shell UDS syslog scripts: `in_syslog_uds_dgram_plaintext_expect.sh`, `in_syslog_uds_stream_plaintext_expect.sh` | Removed from OHOS CTest registration | `source_level_platform_boundary` | r166 showed direct Python `AF_UNIX` bind failed with `EPERM` under the short runtime shell path. r168 removed these two scripts; TCP TLS/plaintext and UDP plaintext syslog shell tests stayed in the supported route and passed. |
| `flb-rt-in_syslog` UDS C subtests: `syslog_unix_perm`, `syslog_tcp_unix`, `syslog_udp_unix` | Removed from `TEST_LIST` | `source_level_platform_boundary` | r161 showed Unix-domain socket permission/bind failures followed by SIGSEGV. r168 removed only the UDS subtests and the supported syslog C subset passed. |
| `flb-rt-in_forward` UDS C subtests: `unix_path`, `unix_perm` | Removed from `TEST_LIST` | `source_level_platform_boundary` | r111/r112 classified the Unix socket subtests as an OHOS UDS permission/path boundary; the non-UDS forward runtime route was kept. |
| `flb-rt-in_tail` inotify, persistent DB, encoding, dockermode, tag, multiline offset, and active-older-file subcases | Removed from `TEST_LIST`; supported tail route uses stat watcher | `source_level_platform_boundary` / `source_level_environment_stability` | OHOS builds set `FLB_INOTIFY=Off`. r36-r43 showed delayed SIGSEGV and timing-sensitive failures in repeated/ordered tail runs. The r170 supported route keeps the stable stat-watcher subset and does not count the omitted inotify and unstable subcases. |
| `flb-rt-in_dummy` copy-count and `flush_on_startup` subcases | Omitted after splitting the original `dummy_flush` unit | `source_level_environment_stability` | The original single acutest entry segfaulted in r11. r53 split stable dummy paths and omitted the copy-count and startup-flush subcases that still reproduced the OHOS crash boundary. |
| `flb-rt-counter_parity_e2e` grouped retry subcases: `retry_drop_route_parity_grouped`, `retry_scheduled_route_parity_grouped` | Removed from `TEST_LIST` | `source_level_environment_stability` | The grouped retry scenarios exercised crash/timing-sensitive retry paths under OHOS. The supported counter parity route stays counted without these two subcases. |
| `flb-rt-custom_calyptia_registration_retry_test` | Excluded with `FLB_WITHOUT_flb-rt-custom_calyptia_registration_retry_test=On` | `source_level_platform_boundary` | r144 failed because Monkey's registration-retry server path references unavailable OHOS pthread cancellation APIs. r146 kept the remaining Calyptia runtime targets and they passed. |
| Historical `_ohos_first_stage_test_exclusions()` CTest names | Not counted unless present in the final registered 177 CTests | `historical_audit_boundary` | These names document the original r4/r10 exploration boundaries. Later targeted probes fixed or classified many root causes, but the final PR claim only counts the registered CTests that passed in r170. |

## Review Rule

When explaining upstream tests outside the 177-test supported route, use the
categories above. Do not describe an item with an uncategorized deferral; that
wording is not a valid review reason.
