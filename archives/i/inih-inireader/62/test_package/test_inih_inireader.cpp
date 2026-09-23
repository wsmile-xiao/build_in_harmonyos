// Consumer test for the inih-inireader package.
// Exercises both the C parser (<ini.h>) and the C++ class (<INIReader.h>)
// through the installed package and checks real parse results (R34).
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

#include <ini.h>
#include <INIReader.h>

namespace {

int g_checks = 0;

void fail(const char *what) {
    std::fprintf(stderr, "FAIL: %s\n", what);
    std::exit(1);
}

void check(bool condition, const char *what) {
    ++g_checks;
    if (!condition) {
        fail(what);
    }
}

const char *kIni =
    "[protocol]\n"
    "version = 6\n"
    "[user]\n"
    "name = Bob Smith\n"
    "active = true\n"
    "pi = 3.14159\n";

int g_pairs = 0;
bool g_values_ok = true;

int handler(void *user, const char *section, const char *name, const char *value) {
    (void)user;
    ++g_pairs;
    if (std::strcmp(section, "protocol") == 0 && std::strcmp(name, "version") == 0 &&
        std::strcmp(value, "6") == 0) {
        return 1;
    }
    if (std::strcmp(section, "user") == 0 && std::strcmp(name, "name") == 0 &&
        std::strcmp(value, "Bob Smith") == 0) {
        return 1;
    }
    if (std::strcmp(section, "user") == 0 && std::strcmp(name, "active") == 0 &&
        std::strcmp(value, "true") == 0) {
        return 1;
    }
    if (std::strcmp(section, "user") == 0 && std::strcmp(name, "pi") == 0 &&
        std::strcmp(value, "3.14159") == 0) {
        return 1;
    }
    g_values_ok = false;
    return 0;
}

}  // namespace

int main() {
    // ── C API ───────────────────────────────────────────────────────────
    int rc = ini_parse_string(kIni, handler, nullptr);
    check(rc == 0, "ini_parse_string returns 0 on success");
    check(g_pairs == 4, "C handler called for all 4 name=value pairs");
    check(g_values_ok, "C handler saw the expected section/name/value triples");

    // ── C++ API ─────────────────────────────────────────────────────────
    INIReader reader(kIni, std::strlen(kIni));
    check(reader.ParseError() == 0, "INIReader::ParseError is 0");
    check(reader.Get("user", "name", "?") == "Bob Smith", "INIReader::Get string");
    check(reader.GetInteger("protocol", "version", -1) == 6, "INIReader::GetInteger");
    check(reader.GetReal("user", "pi", -1.0) > 3.14 &&
              reader.GetReal("user", "pi", -1.0) < 3.15,
          "INIReader::GetReal");
    check(reader.GetBoolean("user", "active", false), "INIReader::GetBoolean true");
    check(reader.Get("user", "missing", "UNKNOWN") == "UNKNOWN", "INIReader default value");
    check(reader.HasSection("user"), "INIReader::HasSection true");
    check(!reader.HasSection("fizz"), "INIReader::HasSection false");
    check(reader.HasValue("user", "name"), "INIReader::HasValue true");
    check(reader.Keys("user").size() == 3, "INIReader::Keys count");

    std::printf("inih-inireader consumer test PASS (%d checks)\n", g_checks);
    return 0;
}
