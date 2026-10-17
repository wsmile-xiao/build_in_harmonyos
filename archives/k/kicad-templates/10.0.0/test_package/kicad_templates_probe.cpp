#include <cstdlib>
#include <cctype>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <set>
#include <sstream>
#include <string>
#include <system_error>
#include <utility>
#include <vector>

#if defined(__OHOS__)
#include <sys/stat.h>
#include <unistd.h>
#endif

namespace fs = std::filesystem;

namespace {

constexpr std::size_t kExpectedProjectCount = 19;
constexpr std::size_t kExpectedTopLevelWorksheetCount = 20;
constexpr std::size_t kExpectedPcbCount = 19;
constexpr std::size_t kExpectedSchCount = 19;
constexpr std::size_t kExpectedProCount = 19;
constexpr std::size_t kExpectedWksCount = 36;
constexpr int kExpectedNamedCheckCount = 20;

const std::set<std::string> kExpectedProjects = {
    "API_Series-500",
    "Arduino_Mega",
    "Arduino_Micro",
    "Arduino_Nano",
    "Arduino_Pro_Mini",
    "Arduino_Uno",
    "BeagleBone-Black-Cape",
    "Edgeberry_Cartridge",
    "EuroCard160mmX100mm",
    "Hammond_1593K_Enclosure",
    "KiCad_MR_diagrams_large_parts",
    "KiCad_MR_diagrams_small_parts",
    "RaspberryPi-HAT",
    "RaspberryPi-uHAT",
    "STM32H7_DevEBox",
    "STM32_Nucleo-64_Morpho",
    "TI-LaunchPad-BoosterPack-20pin",
    "TI-LaunchPad-BoosterPack-40pin",
    "stm32f100-discovery-shield",
};

const std::set<std::string> kExpectedTopLevelWorksheets = {
    "A2_ISO5457-1999_ISO7200-2004-compact_ASMEY1435-2014_EN.kicad_wks",
    "A2_ISO5457-1999_ISO7200-2004-compact_EN.kicad_wks",
    "A2_ISO5457-1999_ISO7200-2004_ASMEY1435-2014_EN.kicad_wks",
    "A2_ISO5457-1999_ISO7200-2004_EN.kicad_wks",
    "A3_ISO5457-1999_ISO7200-2004-compact_ASMEY1435-2014_EN.kicad_wks",
    "A3_ISO5457-1999_ISO7200-2004-compact_EN.kicad_wks",
    "A3_ISO5457-1999_ISO7200-2004_ASMEY1435-2014_EN.kicad_wks",
    "A3_ISO5457-1999_ISO7200-2004_EN.kicad_wks",
    "A4-portrait_ISO5457-1999_ISO7200-2004-compact_ASMEY1435-2014_EN.kicad_wks",
    "A4-portrait_ISO5457-1999_ISO7200-2004-compact_EN.kicad_wks",
    "A4-portrait_ISO5457-1999_ISO7200-2004_ASMEY1435-2014_EN.kicad_wks",
    "A4-portrait_ISO5457-1999_ISO7200-2004_EN.kicad_wks",
    "A4_ISO5457-1999_ISO7200-2004-compact_ASMEY1435-2014_EN.kicad_wks",
    "A4_ISO5457-1999_ISO7200-2004-compact_EN.kicad_wks",
    "A4_ISO5457-1999_ISO7200-2004_ASMEY1435-2014_EN.kicad_wks",
    "A4_ISO5457-1999_ISO7200-2004_EN.kicad_wks",
    "gost_landscape.kicad_wks",
    "gost_portrait.kicad_wks",
    "pagelayout_default.kicad_wks",
    "pagelayout_logo.kicad_wks",
};

struct Results {
    int passed = 0;
    int failed = 0;
    int deferred = 0;
    std::set<std::string> names;

    void check(const std::string& name, bool condition,
               const std::string& detail = {}) {
        names.insert(name);
        if (condition) {
            ++passed;
            std::cout << "[PASS] " << name << '\n';
        } else {
            ++failed;
            std::cerr << "[FAIL] " << name;
            if (!detail.empty()) {
                std::cerr << ": " << detail;
            }
            std::cerr << '\n';
        }
    }

    void defer(const std::string& name, const std::string& detail) {
        names.insert(name);
        ++deferred;
        std::cout << "[DEFERRED] " << name << ": " << detail << '\n';
    }

    int named() const { return passed + failed + deferred; }

    bool count_invariant_holds() const {
        return named() == kExpectedNamedCheckCount &&
               names.size() == static_cast<std::size_t>(named());
    }
};

std::string read_file(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    std::ostringstream contents;
    contents << input.rdbuf();
    return contents.str();
}

bool has_nonempty_file(const fs::path& path) {
    std::error_code error;
    return fs::is_regular_file(path, error) && fs::file_size(path, error) > 0 &&
           !error;
}

class SExpressionParser {
  public:
    explicit SExpressionParser(const std::string& text) : text_(text) {}

    bool parse_document(const std::string& expected_root, bool require_header) {
        skip_whitespace();
        if (!consume('(')) {
            return false;
        }
        skip_whitespace();
        std::string root;
        if (!parse_atom(root) || root != expected_root) {
            return false;
        }

        bool has_version = false;
        bool has_generator = false;
        while (true) {
            skip_whitespace();
            if (at_end()) {
                return false;
            }
            if (consume(')')) {
                break;
            }
            if (peek() == '(') {
                std::string child_head;
                if (!parse_list(child_head, 1)) {
                    return false;
                }
                has_version = has_version || child_head == "version";
                has_generator = has_generator || child_head == "generator";
            } else if (!parse_scalar()) {
                return false;
            }
        }

        skip_whitespace();
        return at_end() &&
               (!require_header || (has_version && has_generator));
    }

  private:
    static constexpr int kMaximumDepth = 512;

    bool parse_list(std::string& head, int depth) {
        if (depth > kMaximumDepth || !consume('(')) {
            return false;
        }
        skip_whitespace();
        if (!parse_atom(head)) {
            return false;
        }
        while (true) {
            skip_whitespace();
            if (at_end()) {
                return false;
            }
            if (consume(')')) {
                return true;
            }
            if (peek() == '(') {
                std::string nested_head;
                if (!parse_list(nested_head, depth + 1)) {
                    return false;
                }
            } else if (!parse_scalar()) {
                return false;
            }
        }
    }

    bool parse_scalar() {
        if (peek() == '"') {
            return parse_quoted_string();
        }
        std::string ignored;
        return parse_atom(ignored);
    }

    bool parse_quoted_string() {
        if (!consume('"')) {
            return false;
        }
        bool escaped = false;
        while (!at_end()) {
            const char character = text_[position_++];
            if (escaped) {
                escaped = false;
            } else if (character == '\\') {
                escaped = true;
            } else if (character == '"') {
                return true;
            }
        }
        return false;
    }

    bool parse_atom(std::string& atom) {
        const std::size_t start = position_;
        while (!at_end()) {
            const unsigned char byte =
                static_cast<unsigned char>(text_[position_]);
            if (std::isspace(byte) || text_[position_] == '(' ||
                text_[position_] == ')' || text_[position_] == '"') {
                break;
            }
            ++position_;
        }
        if (position_ == start) {
            return false;
        }
        atom = text_.substr(start, position_ - start);
        return true;
    }

    void skip_whitespace() {
        while (!at_end() &&
               std::isspace(static_cast<unsigned char>(text_[position_]))) {
            ++position_;
        }
    }

    bool consume(char expected) {
        if (at_end() || text_[position_] != expected) {
            return false;
        }
        ++position_;
        return true;
    }

    bool at_end() const { return position_ == text_.size(); }
    char peek() const { return at_end() ? '\0' : text_[position_]; }

    const std::string& text_;
    std::size_t position_ = 0;
};

bool valid_sexpression(const std::string& text, const std::string& root,
                       bool require_header) {
    return SExpressionParser(text).parse_document(root, require_header);
}

class JsonParser {
  public:
    explicit JsonParser(const std::string& text) : text_(text) {}

    bool parse_project() {
        skip_whitespace();
        if (!parse_object(0, true)) {
            return false;
        }
        skip_whitespace();
        return at_end() && has_board_key_ && has_schematic_key_;
    }

  private:
    static constexpr int kMaximumDepth = 512;

    bool parse_value(int depth) {
        if (depth > kMaximumDepth) {
            return false;
        }
        skip_whitespace();
        if (at_end()) {
            return false;
        }
        switch (peek()) {
            case '{':
                return parse_object(depth, false);
            case '[':
                return parse_array(depth);
            case '"':
                return parse_string(nullptr);
            case 't':
                return parse_literal("true");
            case 'f':
                return parse_literal("false");
            case 'n':
                return parse_literal("null");
            default:
                return peek() == '-' || is_digit(peek()) ? parse_number()
                                                         : false;
        }
    }

    bool parse_object(int depth, bool collect_project_keys) {
        if (depth > kMaximumDepth || !consume('{')) {
            return false;
        }
        skip_whitespace();
        if (consume('}')) {
            return true;
        }
        while (true) {
            std::string key;
            if (!parse_string(&key)) {
                return false;
            }
            if (collect_project_keys) {
                has_board_key_ = has_board_key_ || key == "board";
                has_schematic_key_ = has_schematic_key_ || key == "schematic";
            }
            skip_whitespace();
            if (!consume(':') || !parse_value(depth + 1)) {
                return false;
            }
            skip_whitespace();
            if (consume('}')) {
                return true;
            }
            if (!consume(',')) {
                return false;
            }
            skip_whitespace();
        }
    }

    bool parse_array(int depth) {
        if (depth > kMaximumDepth || !consume('[')) {
            return false;
        }
        skip_whitespace();
        if (consume(']')) {
            return true;
        }
        while (true) {
            if (!parse_value(depth + 1)) {
                return false;
            }
            skip_whitespace();
            if (consume(']')) {
                return true;
            }
            if (!consume(',')) {
                return false;
            }
            skip_whitespace();
        }
    }

    bool parse_string(std::string* decoded) {
        if (!consume('"')) {
            return false;
        }
        if (decoded != nullptr) {
            decoded->clear();
        }
        while (!at_end()) {
            const unsigned char byte =
                static_cast<unsigned char>(text_[position_++]);
            if (byte == '"') {
                return true;
            }
            if (byte < 0x20) {
                return false;
            }
            if (byte != '\\') {
                if (decoded != nullptr) {
                    decoded->push_back(static_cast<char>(byte));
                }
                continue;
            }
            if (at_end()) {
                return false;
            }
            const char escape = text_[position_++];
            if (escape == 'u') {
                for (int index = 0; index < 4; ++index) {
                    if (at_end() || !is_hex_digit(text_[position_++])) {
                        return false;
                    }
                }
                if (decoded != nullptr) {
                    decoded->push_back('?');
                }
            } else {
                const std::string valid_escapes = "\"\\/bfnrt";
                if (valid_escapes.find(escape) == std::string::npos) {
                    return false;
                }
                if (decoded != nullptr) {
                    decoded->push_back(escape);
                }
            }
        }
        return false;
    }

    bool parse_number() {
        consume('-');
        if (consume('0')) {
            if (!at_end() && is_digit(peek())) {
                return false;
            }
        } else {
            if (at_end() || peek() < '1' || peek() > '9') {
                return false;
            }
            while (!at_end() && is_digit(peek())) {
                ++position_;
            }
        }
        if (consume('.')) {
            if (at_end() || !is_digit(peek())) {
                return false;
            }
            while (!at_end() && is_digit(peek())) {
                ++position_;
            }
        }
        if (!at_end() && (peek() == 'e' || peek() == 'E')) {
            ++position_;
            if (!at_end() && (peek() == '+' || peek() == '-')) {
                ++position_;
            }
            if (at_end() || !is_digit(peek())) {
                return false;
            }
            while (!at_end() && is_digit(peek())) {
                ++position_;
            }
        }
        return true;
    }

    bool parse_literal(const std::string& literal) {
        if (text_.compare(position_, literal.size(), literal) != 0) {
            return false;
        }
        position_ += literal.size();
        return true;
    }

    static bool is_digit(char character) {
        return character >= '0' && character <= '9';
    }

    static bool is_hex_digit(char character) {
        return (character >= '0' && character <= '9') ||
               (character >= 'a' && character <= 'f') ||
               (character >= 'A' && character <= 'F');
    }

    void skip_whitespace() {
        while (!at_end() && (peek() == ' ' || peek() == '\t' ||
                             peek() == '\r' || peek() == '\n')) {
            ++position_;
        }
    }

    bool consume(char expected) {
        if (at_end() || peek() != expected) {
            return false;
        }
        ++position_;
        return true;
    }

    bool at_end() const { return position_ == text_.size(); }
    char peek() const { return at_end() ? '\0' : text_[position_]; }

    const std::string& text_;
    std::size_t position_ = 0;
    bool has_board_key_ = false;
    bool has_schematic_key_ = false;
};

bool valid_project_json(const std::string& text) {
    return JsonParser(text).parse_project();
}

class ScopedTemporaryDirectory {
  public:
    ScopedTemporaryDirectory() {
        std::error_code error;
        const fs::path temporary_root = fs::temp_directory_path(error);
        if (error) {
            return;
        }

        const auto nonce = static_cast<unsigned long long>(
            std::chrono::high_resolution_clock::now()
                .time_since_epoch()
                .count());
        for (unsigned int attempt = 0; attempt < 128; ++attempt) {
            const fs::path candidate =
                temporary_root /
                ("kicad-templates-probe-" + std::to_string(nonce) + "-" +
                 std::to_string(attempt));
            error.clear();
            if (fs::create_directory(candidate, error)) {
                path_ = candidate;
                return;
            }
        }
    }

    ~ScopedTemporaryDirectory() {
        cleanup();
    }

    ScopedTemporaryDirectory(const ScopedTemporaryDirectory&) = delete;
    ScopedTemporaryDirectory& operator=(const ScopedTemporaryDirectory&) =
        delete;

    bool valid() const { return !path_.empty(); }
    const fs::path& path() const { return path_; }

    bool cleanup() {
        if (path_.empty()) {
            return true;
        }
        std::error_code error;
        fs::remove_all(path_, error);
        if (error) {
            return false;
        }
        const bool still_exists = fs::exists(path_, error);
        if (error || still_exists) {
            return false;
        }
        path_.clear();
        return true;
    }

  private:
    fs::path path_;
};

bool valid_sexpression_file(const fs::path& path, const std::string& root,
                            bool require_header) {
    return has_nonempty_file(path) &&
           valid_sexpression(read_file(path), root, require_header);
}

bool rejects_truncated_sexpression_file() {
    ScopedTemporaryDirectory temporary_directory;
    if (!temporary_directory.valid()) {
        return false;
    }

    const fs::path fixture =
        temporary_directory.path() / "truncated.kicad_pcb";
    std::ofstream output(fixture, std::ios::binary | std::ios::trunc);
    if (!output) {
        return false;
    }
    output << "(kicad_pcb (version 20241229) "
              "(generator \"pcbnew (quoted)\")";
    output.close();
    if (!output) {
        return false;
    }

    const bool rejected =
        !valid_sexpression_file(fixture, "kicad_pcb", true);
    return temporary_directory.cleanup() && rejected;
}

std::vector<fs::path> files_with_extension(const fs::path& root,
                                           const std::string& extension) {
    std::vector<fs::path> files;
    std::error_code error;
    fs::recursive_directory_iterator iterator(
        root, fs::directory_options::skip_permission_denied, error);
    const fs::recursive_directory_iterator end;
    while (!error && iterator != end) {
        if (iterator->is_regular_file(error) && iterator->path().extension() == extension) {
            files.push_back(iterator->path());
        }
        iterator.increment(error);
    }
    return files;
}

bool all_parse_as_sexpression(const std::vector<fs::path>& files,
                              const std::string& root, bool require_header) {
    for (const auto& file : files) {
        if (!valid_sexpression_file(file, root, require_header)) {
            return false;
        }
    }
    return !files.empty();
}

bool all_parse_as_project_json(const std::vector<fs::path>& files) {
    for (const auto& file : files) {
        if (!valid_project_json(read_file(file))) {
            return false;
        }
    }
    return !files.empty();
}

bool every_project_has_extension(const std::vector<fs::path>& projects,
                                 const std::string& extension) {
    for (const auto& project : projects) {
        bool found = false;
        std::error_code error;
        for (fs::directory_iterator iterator(project, error), end;
             !error && iterator != end; iterator.increment(error)) {
            if (iterator->is_regular_file(error) &&
                iterator->path().extension() == extension) {
                found = true;
                break;
            }
        }
        if (!found) {
            return false;
        }
    }
    return projects.size() == kExpectedProjectCount;
}

}  // namespace

int main(int argc, char* argv[]) {
    if (argc != 2) {
        std::cerr << "usage: kicad_templates_probe <installed-template-root>\n";
        return 2;
    }

    Results results;
    const char* environment = std::getenv("KICAD10_TEMPLATE_DIR");
    const bool environment_exists = environment != nullptr && environment[0] != '\0';
    results.check("environment_exists", environment_exists);

    const fs::path argument_root = fs::path(argv[1]).lexically_normal();
    const fs::path environment_root =
        environment_exists ? fs::path(environment).lexically_normal() : fs::path();
    results.check("environment_equals_argv",
                  environment_exists && environment_root == argument_root);

    std::error_code error;
    const bool root_exists = fs::is_directory(argument_root, error);
    results.check("resource_root_exists", root_exists, argument_root.string());

    std::vector<fs::path> projects;
    std::set<std::string> project_names;
    if (root_exists) {
        for (fs::directory_iterator iterator(argument_root, error), end;
             !error && iterator != end; iterator.increment(error)) {
            if (iterator->is_directory(error)) {
                projects.push_back(iterator->path());
                project_names.insert(iterator->path().filename().string());
            }
        }
    }
    results.check("official_project_directories",
                  projects.size() == kExpectedProjectCount &&
                      project_names == kExpectedProjects,
                  "expected 19 exact project directories");

    std::set<std::string> installed_worksheet_names;
    if (root_exists) {
        for (fs::directory_iterator iterator(argument_root, error), end;
             !error && iterator != end; iterator.increment(error)) {
            if (iterator->is_regular_file(error) &&
                iterator->path().extension() == ".kicad_wks") {
                installed_worksheet_names.insert(
                    iterator->path().filename().string());
            }
        }
    }
    std::size_t top_level_worksheets = 0;
    for (const auto& worksheet : kExpectedTopLevelWorksheets) {
        top_level_worksheets += installed_worksheet_names.count(worksheet);
    }
    results.check("top_level_worksheet_count",
                  top_level_worksheets == kExpectedTopLevelWorksheetCount,
                  "expected all 20 canonical top-level worksheet names");

    const auto pcb_files = files_with_extension(argument_root, ".kicad_pcb");
    const auto sch_files = files_with_extension(argument_root, ".kicad_sch");
    const auto pro_files = files_with_extension(argument_root, ".kicad_pro");
    const auto wks_files = files_with_extension(argument_root, ".kicad_wks");
    results.check("recursive_pcb_count", pcb_files.size() == kExpectedPcbCount,
                  "expected 19");
    results.check("recursive_sch_count", sch_files.size() == kExpectedSchCount,
                  "expected 19");
    results.check("recursive_pro_count", pro_files.size() == kExpectedProCount,
                  "expected 19");
    results.check("recursive_wks_count", wks_files.size() == kExpectedWksCount,
                  "expected 36");

    bool metadata_present = projects.size() == kExpectedProjectCount;
    for (const auto& project : projects) {
        metadata_present = metadata_present &&
                           has_nonempty_file(project / "meta" / "info.html");
    }
    results.check("all_project_metadata", metadata_present);
    results.check("per_project_pcb_presence",
                  every_project_has_extension(projects, ".kicad_pcb"));
    results.check("per_project_sch_presence",
                  every_project_has_extension(projects, ".kicad_sch"));
    results.check("per_project_pro_presence",
                  every_project_has_extension(projects, ".kicad_pro"));

    results.check("pcb_s_expression_syntax",
                  all_parse_as_sexpression(pcb_files, "kicad_pcb", true));
    results.check("sch_s_expression_syntax",
                  all_parse_as_sexpression(sch_files, "kicad_sch", true));
    results.check("pro_json_syntax", all_parse_as_project_json(pro_files));
    results.check("worksheet_s_expression_syntax",
                  all_parse_as_sexpression(wks_files, "page_layout", false));

    const std::string trailing_s_expression =
        "(kicad_pcb (version 20241229) (generator \"pcbnew\")) trailing";
    const std::string second_root_expression =
        "(kicad_pcb (version 20241229) (generator \"pcbnew\")) (extra)";
    const std::string quoted_fake_headers =
        "(kicad_pcb (comment \"(version 1) (generator fake)\"))";
    const std::string nested_fake_headers =
        "(kicad_pcb (group (version 1) (generator fake)))";
    results.check("rejects_truncated_s_expression",
                  rejects_truncated_sexpression_file() &&
                      !valid_sexpression(trailing_s_expression, "kicad_pcb", true) &&
                      !valid_sexpression(second_root_expression, "kicad_pcb", true) &&
                      !valid_sexpression(quoted_fake_headers, "kicad_pcb", true) &&
                      !valid_sexpression(nested_fake_headers, "kicad_pcb", true));
    const std::string malformed_json =
        "{\"board\":{},\"schematic\":{\"broken\":\"unterminated}}";
    const std::string missing_values = "{\"board\":,\"schematic\":}";
    const std::string schematic_only_as_value =
        "{\"board\":{\"description\":\"schematic\"}}";
    results.check("rejects_malformed_json",
                  !valid_project_json(malformed_json) &&
                      !valid_project_json(missing_values) &&
                      !valid_project_json(schematic_only_as_value));

#if defined(__OHOS__)
    bool ohos_access_ok = root_exists && access(argument_root.c_str(), R_OK) == 0;
    struct stat root_status {};
    ohos_access_ok = ohos_access_ok &&
                     stat(argument_root.c_str(), &root_status) == 0 &&
                     S_ISDIR(root_status.st_mode);
    const fs::path representative =
        !pcb_files.empty() ? pcb_files.front() : argument_root / "missing.kicad_pcb";
    struct stat file_status {};
    ohos_access_ok = ohos_access_ok && access(representative.c_str(), R_OK) == 0 &&
                     stat(representative.c_str(), &file_status) == 0 &&
                     S_ISREG(file_status.st_mode);
    results.check("ohos_macro_access_stat_resource_path", ohos_access_ok,
                  representative.string());
#else
    results.defer("ohos_macro_access_stat_resource_path",
                  "host build only; requires the native OHOS compiler and VM");
#endif

    const int named_checks = results.named();
    const bool count_invariant = results.count_invariant_holds();
    if (!count_invariant) {
        std::cerr << "[INTERNAL ERROR] expected " << kExpectedNamedCheckCount
                  << " unique named checks, executed " << named_checks
                  << " across " << results.names.size() << " unique names\n";
    }
    std::cout << "SUMMARY named=" << named_checks << " passed=" << results.passed
              << " failed=" << results.failed
              << " deferred=" << results.deferred << '\n';
    return results.failed == 0 && count_invariant ? 0 : 1;
}
