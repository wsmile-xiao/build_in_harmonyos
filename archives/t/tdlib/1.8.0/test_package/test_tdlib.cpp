//
// tdlib 1.8.0 — consumer test program for the OHOS/Conan package.
//
// Drives the public JSON/C API exported by the packaged libtdjson.so
// (td/telegram/td_json_client.h) and asserts observable behaviour. The
// OH-prefixed checks are OHOS-specific: they pin the platform contract of the
// produced artifact (the OHOS dynamic loader can load and resolve it, the
// loaded image is the very file the build linked, and the gperf-generated MIME
// tables that required the `-Wno-register` build fix really work).
//
// Copyright (c) 2026 OpenHarmony PC adaptation. Distributed under the
// Boost Software License, Version 1.0 (same as upstream TDLib).
//
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <cstdlib>
#include <dlfcn.h>

#include <cstdio>
#include <cstring>
#include <string>

#include "td/telegram/td_json_client.h"

#ifndef EXPECTED_TDJSON_PATH
#define EXPECTED_TDJSON_PATH "libtdjson.so"
#endif

namespace {

int checks = 0;
int failures = 0;

void check(bool ok, const std::string &what) {
  ++checks;
  if (!ok) {
    ++failures;
    std::printf("  [FAIL] %s\n", what.c_str());
  } else {
    std::printf("  [ ok ] %s\n", what.c_str());
  }
}

bool contains(const char *haystack, const std::string &needle) {
  if (haystack == nullptr) {
    return false;
  }
  return std::string(haystack).find(needle) != std::string::npos;
}

std::string text_of(const char *response) {
  if (response == nullptr) {
    return std::string();
  }
  const std::string body(response);
  const std::string key = "\"text\":\"";
  auto pos = body.find(key);
  if (pos == std::string::npos) {
    return std::string();
  }
  pos += key.size();
  auto end = body.find('"', pos);
  if (end == std::string::npos) {
    return std::string();
  }
  return body.substr(pos, end - pos);
}

// OH-1: the OHOS dynamic loader must be able to load the packaged shared
// library and resolve every public entry point.
void check_dynamic_loading() {
  std::printf("OH-1 OHOS dynamic loader loads libtdjson.so\n");
  std::printf("       artifact: %s\n", EXPECTED_TDJSON_PATH);
  void *handle = dlopen(EXPECTED_TDJSON_PATH, RTLD_NOW | RTLD_LOCAL);
  if (handle == nullptr) {
    const char *err = dlerror();
    check(false, std::string("dlopen failed: ") + (err ? err : "?"));
    return;
  }
  check(true, "dlopen(artifact, RTLD_NOW)");
  const char *symbols[] = {"td_execute",
                           "td_json_client_create",
                           "td_json_client_send",
                           "td_json_client_receive",
                           "td_json_client_execute",
                           "td_json_client_destroy"};
  for (const char *name : symbols) {
    check(dlsym(handle, name) != nullptr, std::string("dlsym ") + name);
  }
  dlclose(handle);
}

// OH-2: the image actually loaded at runtime must be the artifact the build
// linked against (not a system copy of the same name).
void check_loaded_image_is_packaged() {
  std::printf("OH-2 loaded image is the packaged artifact\n");
  Dl_info info;
  std::memset(&info, 0, sizeof(info));
  if (dladdr(reinterpret_cast<void *>(&td_execute), &info) == 0 ||
      info.dli_fname == nullptr) {
    check(false, "dladdr(td_execute)");
    return;
  }
  const std::string path(info.dli_fname);
  std::printf("       loaded path: %s\n", path.c_str());
  char loaded_real[4096] = {0};
  char expected_real[4096] = {0};
  const bool resolved =
      realpath(path.c_str(), loaded_real) != nullptr &&
      realpath(EXPECTED_TDJSON_PATH, expected_real) != nullptr;
  check(resolved && std::string(loaded_real) == std::string(expected_real),
        std::string("resolved image == linked artifact (") + EXPECTED_TDJSON_PATH + ")");
  check(path.find("/usr/lib") != 0 && path.find("/system/") != 0 &&
            path.find("/vendor/") != 0,
        "artifact is not a system library image");
}

// OH-3: the gperf-generated MIME tables (the C++17 `register` incompatibility
// that the recipe works around with -Wno-register) must deliver correct
// results on OHOS.
void check_mime_tables() {
  std::printf("OH-3 gperf-generated MIME tables on OHOS\n");
  struct Case {
    const char *file_name;
    const char *expected;
  };
  const Case cases[] = {{"index.html", "text/html"},
                        {"d.txt", "text/plain"},
                        {"b.png", "image/png"},
                        {"a.json", "application/json"}};
  for (const auto &c : cases) {
    const std::string request =
        std::string("{\"@type\":\"getFileMimeType\",\"file_name\":\"") + c.file_name + "\"}";
    const char *response = td_execute(request.c_str());
    check(text_of(response) == c.expected,
          std::string("getFileMimeType(") + c.file_name + ") == " + c.expected);
  }
  const char *rev = td_execute("{\"@type\":\"getFileExtension\",\"mime_type\":\"text/html\"}");
  check(text_of(rev) == "html", "getFileExtension(text/html) == html");
}

// OH-4: text entity extraction — exercises the packaged tdlib text logic.
void check_text_entities() {
  std::printf("OH-4 text entity extraction\n");
  const char *response = td_execute(
      "{\"@type\":\"getTextEntities\",\"text\":"
      "\"@telegram /test_command https://telegram.org\"}");
  check(contains(response, "\"@type\":\"textEntities\""), "response is textEntities");
  check(contains(response, "textEntityTypeMention"), "mention entity found");
  check(contains(response, "textEntityTypeBotCommand"), "bot command entity found");
  check(contains(response, "textEntityTypeUrl"), "url entity found");

  const char *parsed = td_execute(
      "{\"@type\":\"parseTextEntities\",\"text\":\"<b>bold</b>\","
      "\"parse_mode\":{\"@type\":\"textParseModeMarkdown\",\"version\":1}}");
  check(contains(parsed, "\"@type\":\"formattedText\""), "parseTextEntities returns formattedText");
}

// OH-5: the packaged static toolchain + JSON client must initialise a full
// TDLib instance and report the upstream version.
void check_client_and_version() {
  std::printf("OH-5 full TDLib client initialisation\n");
  void *client = td_json_client_create();
  check(client != nullptr, "td_json_client_create()");
  if (client == nullptr) {
    return;
  }
  td_json_client_execute(client, "{\"@type\":\"setLogVerbosityLevel\",\"new_verbosity_level\":0}");

  const char *sync = td_json_client_execute(
      client, "{\"@type\":\"getLogVerbosityLevel\"}");
  check(contains(sync, "\"@type\":\"logVerbosityLevel\""),
        "td_json_client_execute(getLogVerbosityLevel)");

  bool version_seen = false;
  for (int i = 0; i < 20 && !version_seen; ++i) {
    const char *update = td_json_client_receive(client, 1.0);
    if (update == nullptr) {
      continue;
    }
    if (contains(update, "\"version\"") && contains(update, "\"1.8.0\"")) {
      version_seen = true;
    }
  }
  check(version_seen, "updateOption reports TDLib version 1.8.0");

  td_json_client_destroy(client);
  check(true, "td_json_client_destroy()");
}

}  // namespace

int main() {
  std::printf("tdlib consumer test — language level: %ld\n",
              static_cast<long>(__cplusplus));
  td_execute("{\"@type\":\"setLogVerbosityLevel\",\"new_verbosity_level\":0}");
  check_dynamic_loading();
  check_loaded_image_is_packaged();
  check_mime_tables();
  check_text_entities();
  check_client_and_version();

  std::printf("TD_PACKAGE_RESULT checks=%d failed=%d\n", checks, failures);
  std::printf("%s\n", failures == 0 ? "ALL CHECKS PASSED" : "CHECKS FAILED");
  return failures == 0 ? 0 : 1;
}
