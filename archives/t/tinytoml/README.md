# tinytoml

A header-only C++11 library for parsing TOML (Tom's Obvious, Minimal Language).

## Description

tinytoml is a tiny TOML parser for C++11 with the following properties:
- Header file only (just copy `include/toml/toml.h` into your project)
- C++11 library friendly (array is `std::vector`, table is `std::map`, time is `std::chrono::system_clock::time_point`)
- No external dependencies (gtest is bundled for testing only)
- Based on TOML v0.4.0 specification

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 0.4.0 | published | Header-only library, CMake build for tests |

## Usage

```cpp
#include <toml/toml.h>
#include <fstream>

std::ifstream ifs("config.toml");
toml::ParseResult pr = toml::parse(ifs);

if (pr.valid()) {
    const toml::Value* v = pr.value.find("key");
    if (v && v->is<std::string>()) {
        std::cout << v->as<std::string>() << std::endl;
    }
}
```

## Source

- Repository: https://github.com/mayah/tinytoml
- License: Simplified BSD License
