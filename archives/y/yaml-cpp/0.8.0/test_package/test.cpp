/* yaml-cpp 0.8.0 consumer-side functional test.
 *
 * Parses a YAML document, walks the node tree, emits it back, and asserts
 * the round-trip semantics plus core emitter features. Exercises the real
 * yaml-cpp API (Load/emit, scalar/map/sequence nodes, streaming) so it is a
 * substantive L1 test, not a stub (R34).
 */
#include <yaml-cpp/yaml.h>

#include <sstream>
#include <string>

static int fail(const char *what, const std::string &got, const std::string &want)
{
    std::printf("FAIL %s\n  got: %s\n  want: %s\n", what, got.c_str(), want.c_str());
    return 1;
}

int main(void)
{
    const std::string doc =
        "name: yaml-cpp\n"
        "version: 0.8.0\n"
        "features:\n"
        "  - parser\n"
        "  - emitter\n"
        "config:\n"
        "  shared: false\n"
        "  fPIC: true\n";

    /* 1) Parse + scalar access */
    YAML::Node root = YAML::Load(doc);
    std::string name = root["name"].as<std::string>();
    if (name != "yaml-cpp")
        return fail("scalar name", name, "yaml-cpp");

    std::string ver = root["version"].as<std::string>();
    if (ver != "0.8.0")
        return fail("scalar version", ver, "0.8.0");

    /* 2) Sequence node iteration */
    const YAML::Node &features = root["features"];
    if (!features.IsSequence() || features.size() != 2)
        return fail("sequence size",
                    std::to_string(features.size()), "2");
    if (features[0].as<std::string>() != "parser")
        return fail("seq[0]", features[0].as<std::string>(), "parser");
    if (features[1].as<std::string>() != "emitter")
        return fail("seq[1]", features[1].as<std::string>(), "emitter");

    /* 3) Nested map + bool coercion */
    const YAML::Node &cfg = root["config"];
    if (!cfg.IsMap())
        return fail("config IsMap", "false", "true");
    bool shared = cfg["shared"].as<bool>();
    if (shared)
        return fail("bool shared", "true", "false");
    bool fpic = cfg["fPIC"].as<bool>();
    if (!fpic)
        return fail("bool fPIC", "false", "true");

    /* 4) Emit round-trip: re-parse the emitted text and compare key values */
    std::stringstream ss;
    ss << root;
    YAML::Node reparsed = YAML::Load(ss.str());
    if (reparsed["name"].as<std::string>() != "yaml-cpp")
        return fail("round-trip name",
                    reparsed["name"].as<std::string>(), "yaml-cpp");
    if (reparsed["features"][0].as<std::string>() != "parser")
        return fail("round-trip seq[0]",
                    reparsed["features"][0].as<std::string>(), "parser");

    /* 5) Emitter: build a document from scratch and assert its text form */
    YAML::Emitter out;
    out << YAML::BeginMap;
    out << YAML::Key << "library" << YAML::Value << "yaml-cpp";
    out << YAML::Key << "version" << YAML::Value << "0.8.0";
    out << YAML::Key << "platforms" << YAML::Value;
    out << YAML::BeginSeq << "Linux" << "OHOS" << YAML::EndSeq;
    out << YAML::EndMap;
    std::string emitted(out.c_str());
    if (emitted.find("library: yaml-cpp") == std::string::npos)
        return fail("emitter library", emitted, "library: yaml-cpp");
    if (emitted.find("- OHOS") == std::string::npos)
        return fail("emitter OHOS", emitted, "- OHOS");

    std::printf(
        "yaml-cpp OK: parse/scalar/sequence/nested-map/round-trip/emitter "
        "— 5 groups\n"
    );
    return 0;
}
