// HarmonyOS PC consumer smoke test for libgrpc_authorization_provider 1.82.0.
//
// Exercises the module's C-core API surface (include/grpc/grpc_security.h):
// the CEL-based authorization policy engine behind
// grpc_authorization_policy_provider_static_data_create /
// grpc_authorization_policy_provider_file_watcher_create /
// grpc_authorization_policy_provider_release, plus the gRPC version symbols
// embedded in the archive (the C core is compiled in).
//
// Note: the C++ binding (grpcpp/security/authorization_policy_provider.h,
// class StaticDataAuthorizationPolicyProvider) is NOT part of the upstream
// grpc_authorization_provider library target — upstream compiles that TU
// only into its own test binaries (src/cpp/server/
// authorization_policy_provider.cc is referenced solely by
// authorization_policy_provider_test in CMakeLists.txt). The module's
// consumable API is therefore the C core below.

#include <grpc/grpc.h>
#include <grpc/grpc_security.h>
#include <grpc/status.h>

#include <cstdio>
#include <cstring>

int main() {
  // The C core is embedded in libgrpc_authorization_provider.a; version
  // symbols prove the archive linked and resolved at runtime.
  // Use explicit checks instead of assert(): assert() is compiled out under
  // NDEBUG (default Release), which would silently void the smoke test.
  const char* c_version = grpc_version_string();
  if (c_version == nullptr || c_version[0] == '\0') {
    std::fprintf(stderr, "test_package: FAILED, grpc_version_string() empty\n");
    return 1;
  }
  std::printf("grpc core version: %s\n", c_version);

  // 1) Valid CEL-based policy: the provider factory must succeed and the
  //    underlying authorization engine must be constructed (policy parsed,
  //    matchers built). This exercises the authorization engine code the
  //    module ships (evaluate_args / matchers / grpc_authorization_engine).
  // Policy schema per grpc 1.82 (RBAC v1): top-level name + allow_rules /
  // deny_rules, matching upstream's own test fixture
  // test/core/security/authorization/test_policies/valid_policy_1.json.
  const char* valid_policy =
      "{"
      "\"name\": \"authz\","
      "\"allow_rules\": ["
      "  {"
      "   \"name\": \"allow_echo\","
      "   \"request\": {"
      "    \"paths\": [\"*/Echo\"],"
      "    \"headers\": ["
      "     {\"key\": \"key-foo\", \"values\": [\"foo1\", \"foo2\"]},"
      "     {\"key\": \"key-bar\", \"values\": [\"bar1\"]}"
      "    ]"
      "   }"
      "  }"
      "],"
      "\"deny_rules\": ["
      "  {"
      "   \"name\": \"deny_clientstreamingecho\","
      "   \"request\": {\"paths\": [\"*/ClientStreamingEcho\"]}"
      "  }"
      "]"
      "}";
  grpc_status_code code = GRPC_STATUS_OK;
  const char* error_details = nullptr;
  grpc_authorization_policy_provider* provider =
      grpc_authorization_policy_provider_static_data_create(
          valid_policy, &code, &error_details);
  if (provider == nullptr || code != GRPC_STATUS_OK) {
    std::fprintf(stderr,
                 "test_package: FAILED, valid policy rejected: code=%d details=%s\n",
                 static_cast<int>(code),
                 error_details ? error_details : "()");
    return 1;
  }
  grpc_authorization_policy_provider_release(provider);
  std::printf("valid policy: provider created and released\n");

  // 2) Invalid policy: the factory must fail with a parse error — proves
  //    the CEL/policy parser really runs (not a stub).
  const char* invalid_policy = "{ not a valid policy";
  code = GRPC_STATUS_OK;
  error_details = nullptr;
  grpc_authorization_policy_provider* bad_provider =
      grpc_authorization_policy_provider_static_data_create(
          invalid_policy, &code, &error_details);
  if (bad_provider != nullptr || code == GRPC_STATUS_OK) {
    std::fprintf(stderr, "test_package: FAILED, invalid policy accepted\n");
    grpc_authorization_policy_provider_release(bad_provider);
    return 1;
  }
  std::printf("invalid policy: rejected (code=%d, parser active)\n",
              static_cast<int>(code));

  // 3) File-watcher provider with a non-existent path: must fail cleanly
  //    (error path of the watcher provider, exercises gpr file polling).
  code = GRPC_STATUS_OK;
  error_details = nullptr;
  grpc_authorization_policy_provider* watch_provider =
      grpc_authorization_policy_provider_file_watcher_create(
          "$TMPDIR/nonexistent_authz_policy.json", 1, &code, &error_details);
  if (watch_provider != nullptr || code == GRPC_STATUS_OK) {
    std::fprintf(stderr, "test_package: FAILED, nonexistent file accepted\n");
    grpc_authorization_policy_provider_release(watch_provider);
    return 1;
  }
  std::printf("file watcher (missing file): rejected (code=%d)\n",
              static_cast<int>(code));

  std::printf("test_package: OK\n");
  return 0;
}
