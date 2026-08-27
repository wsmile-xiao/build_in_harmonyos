# simdjson for HarmonyOS

## Overview

simdjson is a JSON parser that uses SIMD instructions to achieve extremely high parsing throughput. This package provides the simdjson library adapted for HarmonyOS/OpenHarmony (aarch64).

## Software Info

| Field | Value |
|-------|-------|
| Name | simdjson |
| Version | 4.6.3 |
| Source | https://github.com/simdjson/simdjson/archive/refs/tags/v4.6.3.tar.gz |
| License | Apache-2.0 |
| Homepage | https://simdjson.org/ |

## Build

```bash
# Conan-based build (recommended)
conan create . --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64
```

## Dependencies

None. simdjson is self-contained, only requires system pthread.

## Installation

```bash
# Install via Conan
conan install --requires="simdjson/4.6.3@ohpcd/stable" -pr:h=ci/conan/profiles/ohos-aarch64
```

## Usage

```cpp
#include <simdjson.h>

simdjson::ondemand::parser parser;
auto json = simdjson::padded_string::load("data.json");
auto doc = parser.iterate(json);
```

Link with: `-lsimdjson -lpthread`
