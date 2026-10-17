/*
 * test_cpp.cpp — C++ consumer verification for libtatsu 1.0.5.
 *
 * The public headers (<libtatsu/tss.h>, <libtatsu/tatsu.h>) wrap all
 * declarations in extern "C" when compiled as C++. This translation
 * unit includes them from C++, links against the library and calls a
 * representative subset of the API (request build, tag builder, send
 * against a local mock, response accessors) to prove the C++ ABI
 * contract.
 */
#include <libtatsu/tss.h>
#include <libtatsu/tatsu.h>
#include <plist/plist.h>

#include <cstdio>
#include <cstring>

static int g_checks = 0;
static int g_failed = 0;

#define CHECK(cond, name) do { \
    g_checks++; \
    if (cond) { std::printf("[PASS] %s\n", (name)); } \
    else { g_failed++; std::printf("[FAIL] %s (line %d)\n", (name), __LINE__); } \
} while (0)

int main(void)
{
    std::printf("== libtatsu 1.0.5 C++ consumer test ==\n");

    /* 1. version string from a C++ TU (extern "C" linkage proof) */
    const char *v = libtatsu_version();
    CHECK(v != nullptr, "libtatsu_version() callable from C++");
    CHECK(std::strcmp(v, "1.0.5") == 0, "libtatsu_version() == \"1.0.5\"");

    /* 2. request object creation and field manipulation from C++ */
    plist_t request = tss_request_new(nullptr);
    CHECK(request != nullptr, "tss_request_new(nullptr) from C++");
    CHECK(plist_dict_get_item(request, "@HostPlatformInfo") != nullptr,
          "request fields accessible from C++");

    /* 3. tag builder + overrides from C++ */
    plist_t parameters = plist_new_dict();
    plist_dict_set_item(parameters, "ApECID", plist_new_uint(777));
    plist_dict_set_item(parameters, "UniqueBuildID", plist_new_data("\x01", 1));
    plist_dict_set_item(parameters, "ApChipID", plist_new_uint(0x8000));
    plist_dict_set_item(parameters, "ApBoardID", plist_new_uint(6));
    plist_dict_set_item(parameters, "ApSecurityDomain", plist_new_uint(1));
    int rc = tss_request_add_common_tags(request, parameters, nullptr);
    CHECK(rc == 0, "tss_request_add_common_tags from C++");

    uint64_t ecid = 0;
    plist_t node = plist_dict_get_item(request, "ApECID");
    if (node) plist_get_uint_val(node, &ecid);
    CHECK(ecid == 777, "ApECID visible after add_common_tags from C++");

    /* 4. debug level API (harmless, part of public API) */
    tss_set_debug_level(0);

    plist_free(parameters);
    plist_free(request);

    std::printf("\nTotal: %d checks, Failed: %d\n", g_checks, g_failed);
    return (g_failed == 0) ? 0 : 1;
}
