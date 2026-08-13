#include <absl/base/config.h>
#include <absl/container/flat_hash_map.h>
#include <absl/status/status.h>
#include <absl/status/statusor.h>
#include <absl/strings/str_cat.h>

#include <cstdio>
#include <string>

static_assert(ABSL_LTS_RELEASE_VERSION == 20260526);
static_assert(ABSL_LTS_RELEASE_PATCH_LEVEL == 0);

absl::StatusOr<int> Lookup(
    const absl::flat_hash_map<std::string, int>& values,
    const std::string& key) {
    const auto it = values.find(key);
    if (it == values.end()) {
        return absl::NotFoundError(absl::StrCat("missing key: ", key));
    }
    return it->second;
}

int main() {
    const absl::flat_hash_map<std::string, int> values = {
        {"harmony", 6},
        {"abseil", 20260526},
    };
    if (values.size() != 2) {
        return 1;
    }

    const absl::StatusOr<int> found = Lookup(values, "harmony");
    if (!found.ok()) {
        return 2;
    }
    if (*found != 6) {
        return 3;
    }

    const absl::StatusOr<int> missing = Lookup(values, "ohos");
    if (missing.ok()) {
        return 4;
    }
    if (missing.status().code() != absl::StatusCode::kNotFound) {
        return 5;
    }

    const std::string summary = absl::StrCat("abseil-", values.at("abseil"));
    if (summary != "abseil-20260526") {
        return 6;
    }

    std::printf("%s\n", summary.c_str());
    return 0;
}
