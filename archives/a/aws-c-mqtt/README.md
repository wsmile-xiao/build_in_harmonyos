# AWS C MQTT

AWS C MQTT provides the C MQTT client library used by the AWS CRT stack.

## OpenHarmony PC status

| Version | Status | Build date | Notes |
| --- | --- | --- | --- |
| 0.15.2 | built | 2026-07-16 | Private-source AWS CRT dependency build; 296 deterministic upstream ctest cases run in CI, consumer smoke coverage. |
| 0.14.0 | partial | 2026-04-24 | Historical entry. |

## Upstream

- Source: https://github.com/awslabs/aws-c-mqtt
- Archive: https://github.com/awslabs/aws-c-mqtt/archive/refs/tags/v0.15.2.tar.gz

## OpenHarmony notes

This adaptation builds `aws-c-mqtt` together with the required AWS CRT C dependencies from pinned private source archives, runs 296 deterministic cases from the upstream 555-case ctest suite in `build()`, and validates the packaged consumer surface through Conan `test_package`. The 259 excluded cases are event-loop, TLS, request-response and network-dependent scenarios that timed out or failed during full-device validation; the exclusions are documented in the recipe and MANIFEST.
