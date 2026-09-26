// test_config-loader.cpp — consumer verification for config-loader 1.0
//
// Simulates a business-layer application that loads its service configuration
// via config-loader's public API only (DEFINE_SCHEMA + loadJSON2Obj), using
// the installed headers and the packaged libconfig-loader.a.
#include <config-loader/ConfigLoader.h>

#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>

using namespace CONFIG_LOADER_NS;

// Business schema: an "order service" application config
DEFINE_SCHEMA(ServiceConfig,
              (std::string) service_name,
              (std::string) host,
              (uint16_t) port,
              (bool) enable_tls,
              (std::vector<int>) retry_backoff_ms);

// Nested schema to exercise compound deserialization through public API
DEFINE_SCHEMA(AppConfig,
              (ServiceConfig) service,
              (std::string) log_level);

int main() {
    int failures = 0;

    // Load a JSON config from an inline string (business case: remote config)
    AppConfig cfg;
    auto res = loadJSON2Obj(cfg, [] {
        return R"({
            "service": {
                "service_name": "order-service",
                "host": "192.168.1.10",
                "port": 8443,
                "enable_tls": true,
                "retry_backoff_ms": [100, 200, 400]
            },
            "log_level": "info"
        })";
    });

    if (res != Result::SUCCESS) {
        printf("[config-loader consumer] FAIL: load returned code %d\n", static_cast<int>(res));
        return 1;
    }

    printf("[config-loader consumer] loaded service_name=%s host=%s port=%u "
           "tls=%d retries=%zu log_level=%s\n",
           cfg.service.service_name.c_str(),
           cfg.service.host.c_str(),
           static_cast<unsigned>(cfg.service.port),
           cfg.service.enable_tls ? 1 : 0,
           cfg.service.retry_backoff_ms.size(),
           cfg.log_level.c_str());

    if (cfg.service.service_name != "order-service") ++failures;
    if (cfg.service.host != "192.168.1.10") ++failures;
    if (cfg.service.port != 8443) ++failures;
    if (!cfg.service.enable_tls) ++failures;
    if (cfg.service.retry_backoff_ms.size() != 3) ++failures;
    if (cfg.service.retry_backoff_ms[0] != 100) ++failures;
    if (cfg.service.retry_backoff_ms[2] != 400) ++failures;
    if (cfg.log_level != "info") ++failures;

    // Error path: a missing field must be reported, not silently accepted
    AppConfig bad;
    auto badRes = loadJSON2Obj(bad, [] { return R"({"service": {"service_name": "x"}})"; });
    printf("[config-loader consumer] missing-field result=%d (expect ERR_MISSING_FIELD=%d)\n",
           static_cast<int>(badRes), static_cast<int>(Result::ERR_MISSING_FIELD));
    if (badRes != Result::ERR_MISSING_FIELD) ++failures;

    if (failures == 0) {
        printf("[config-loader consumer] PASS: all schema fields deserialized correctly\n");
        return 0;
    }
    printf("[config-loader consumer] FAIL: %d check(s) failed\n", failures);
    return 1;
}
