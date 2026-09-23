// test_orcus.cpp — consumer test for liborcus 0.21.0 (R34: real API calls).
//
// Exercises the packaged libraries the way a downstream consumer would:
// CSV parsing (liborcus-parser), JSON parsing (liborcus-parser),
// string interning (liborcus-parser), base64 codec (liborcus-parser) and
// SAX XML parsing (liborcus-parser). Each CHECK prints an
// "ORCUS-CHECK <name> ok" line; the test_package conanfile counts those
// lines for the HMBS_TEST_PACKAGE_RESULT marker. Exit code is 0 only if
// all 15 checks pass.

#include <orcus/base64.hpp>
#include <orcus/csv_parser.hpp>
#include <orcus/json_parser.hpp>
#include <orcus/sax_parser.hpp>
#include <orcus/string_pool.hpp>

#include <cstdint>
#include <cstdio>
#include <string>
#include <string_view>
#include <vector>

namespace {

int g_failed = 0;
int g_passed = 0;

void check(const char* name, bool condition)
{
    if (condition)
    {
        ++g_passed;
        std::printf("ORCUS-CHECK %s ok\n", name);
    }
    else
    {
        ++g_failed;
        std::printf("ORCUS-CHECK %s FAIL\n", name);
    }
    std::fflush(stdout);
}

struct csv_collector : public orcus::csv_handler
{
    int rows = 0;
    std::vector<std::string> cells;

    void begin_row() {}
    void end_row() { ++rows; }
    void cell(std::string_view value, bool /*transient*/)
    {
        // Copy immediately: transient values are only valid in-scope.
        cells.emplace_back(value.data(), value.size());
    }
};

void test_csv_basic()
{
    const char* content = "name,age\nAlice,30\nBob,25\n";
    csv_collector hdl;
    orcus::csv::parser_config config;
    // parser_config defaults to empty delimiters and NUL text qualifier
    // (see src/parser/csv_parser_base.cpp); without these the whole line
    // becomes one cell (3 cells, not 6) and hdl.cells.at(5) throws
    // std::out_of_range. Match the production default ("," / '"').
    config.delimiters = ",";
    config.text_qualifier = '"';
    orcus::csv_parser<csv_collector> parser(content, hdl, config);
    parser.parse();
    check("csv-rows", hdl.rows == 3);
    check("csv-cells", hdl.cells.size() == 6);
    check("csv-first-cell", hdl.cells.size() > 0 && hdl.cells[0] == "name");
    check("csv-last-cell", hdl.cells.size() > 5 && hdl.cells[5] == "25");
}

void test_csv_quoted()
{
    const char* content = "\"x,y\",z\n";
    csv_collector hdl;
    orcus::csv::parser_config config;
    config.delimiters = ",";
    config.text_qualifier = '"';
    orcus::csv_parser<csv_collector> parser(content, hdl, config);
    parser.parse();
    check("csv-quoted",
          hdl.rows == 1 && hdl.cells.size() == 2
          && hdl.cells.size() > 1 && hdl.cells[0] == "x,y" && hdl.cells[1] == "z");
}

void test_string_pool()
{
    orcus::string_pool pool;
    auto first = pool.intern("hello");
    check("pool-new", first.second);
    auto second = pool.intern("hello");
    check("pool-reuse", !second.second && second.first == first.first);
    pool.intern("world");
    check("pool-size", pool.size() == 2);
}

void test_base64()
{
    const std::vector<uint8_t> man = {'M', 'a', 'n'};
    check("b64-encode", orcus::encode_to_base64(man) == "TWFu");
    const std::vector<uint8_t> raw = {0, 1, 2, 250, 255};
    check("b64-roundtrip", orcus::decode_from_base64(orcus::encode_to_base64(raw)) == raw);
}

struct json_collector : public orcus::json_handler
{
    int objects = 0;
    int arrays = 0;
    int keys = 0;
    int numbers = 0;
    double total = 0.0;

    void begin_object() { ++objects; }
    void begin_array() { ++arrays; }
    void object_key(std::string_view /*key*/, bool /*transient*/) { ++keys; }
    void number(double val) { ++numbers; total += val; }
};

void test_json()
{
    const char* content = "{\"a\": 1, \"b\": [true, null, \"x\"]}";
    json_collector hdl;
    orcus::json_parser<json_collector> parser(content, hdl);
    parser.parse();
    check("json-objects", hdl.objects == 1);
    check("json-arrays", hdl.arrays == 1);
    check("json-keys", hdl.keys == 2);
    check("json-numbers", hdl.numbers == 1 && hdl.total == 1.0);
}

struct sax_collector : public orcus::sax_handler
{
    int starts = 0;
    int ends = 0;

    void start_element(const orcus::sax::parser_element& /*elem*/) { ++starts; }
    void end_element(const orcus::sax::parser_element& /*elem*/) { ++ends; }
};

void test_sax()
{
    const char* content = "<root><a>1</a></root>";
    sax_collector hdl;
    orcus::sax_parser<sax_collector> parser(content, hdl);
    parser.parse();
    check("sax-elements", hdl.starts == 2 && hdl.ends == 2);
}

} // namespace

int main()
{
    test_csv_basic();
    test_csv_quoted();
    test_string_pool();
    test_base64();
    test_json();
    test_sax();
    std::printf("ORCUS-CHECK-SUMMARY passed=%d failed=%d total=15\n",
                g_passed, g_failed);
    std::fflush(stdout);
    return g_failed == 0 ? 0 : 1;
}
