// test_package.cpp — exercise the mstch public API (mstch::render)
//
// Covers: variable substitution, section (truthy/falsy), list iteration,
// escaping, partials, and exact string matching of the rendered output.

#include <mstch/mstch.hpp>

#include <cassert>
#include <iostream>
#include <string>
#include <map>

static int failures = 0;

static void check(const std::string& label, const std::string& got, const std::string& want) {
    if (got != want) {
        std::cerr << "FAIL " << label << "\n  got:  [" << got << "]\n  want: [" << want << "]\n";
        ++failures;
    } else {
        std::cout << "PASS " << label << "  =>  [" << got << "]\n";
    }
}

int main() {
    // 1) Simple variable substitution
    {
        mstch::map ctx{{"name", std::string("world")}};
        std::string out = mstch::render("Hello {{name}}!", ctx);
        check("variable", out, "Hello world!");
    }

    // 2) Escaping (default HTML escape). mstch also escapes '/' as
    //    "&#x2F;" (src/utils.cpp), so the expected value reflects that.
    {
        mstch::map ctx{{"html", std::string("<b>&amp;</b>")}};
        std::string out = mstch::render("{{html}}", ctx);
        check("escaping", out, "&lt;b&gt;&amp;amp;&lt;&#x2F;b&gt;");
    }

    // 3) Unescaped variable (triple-mustache {{{...}}})
    {
        mstch::map ctx{{"raw", std::string("<b>bold</b>")}};
        std::string out = mstch::render("{{{raw}}}", ctx);
        check("unescaped", out, "<b>bold</b>");
    }

    // 4) Section — truthy
    {
        mstch::map ctx{{"show", true}};
        std::string out = mstch::render("{{#show}}visible{{/show}}", ctx);
        check("section_truthy", out, "visible");
    }

    // 5) Section — falsy (empty/false value omits the block)
    {
        mstch::map ctx{{"show", false}};
        std::string out = mstch::render("{{#show}}visible{{/show}}", ctx);
        check("section_falsy", out, "");
    }

    // 6) List iteration (section over a non-empty array)
    {
        mstch::array items{
            mstch::map{{"name", std::string("Alice")}},
            mstch::map{{"name", std::string("Bob")}},
            mstch::map{{"name", std::string("Carol")}},
        };
        mstch::map ctx{{"items", items}};
        std::string out = mstch::render(
            "{{#items}}- {{name}}\n{{/items}}", ctx);
        check("list_iteration", out, "- Alice\n- Bob\n- Carol\n");
    }

    // 7) Empty list section renders nothing
    {
        mstch::map ctx{{"items", mstch::array{}}};
        std::string out = mstch::render("{{#items}}x{{/items}}", ctx);
        check("empty_list", out, "");
    }

    // 8) Inverted section — renders when value is falsy
    {
        mstch::map ctx{{"empty", false}};
        std::string out = mstch::render("{{^empty}}none{{/empty}}", ctx);
        check("inverted_section", out, "none");
    }

    // 9) Comments are stripped
    {
        mstch::map ctx{};
        std::string out = mstch::render("a{{! comment }}b", ctx);
        check("comment", out, "ab");
    }

    // 10) Partials
    {
        mstch::map ctx{{"name", std::string("mstch")}};
        std::map<std::string, std::string> partials{{"greeting", "Hello {{name}}!"}};
        std::string out = mstch::render("{{>greeting}}", ctx, partials);
        check("partial", out, "Hello mstch!");
    }

    // 11) Nested context (object with sub-map)
    {
        mstch::map person{{"name", std::string("Dave")}};
        mstch::map ctx{{"person", person}};
        std::string out = mstch::render("{{person.name}}", ctx);
        check("dotted_key", out, "Dave");
    }

    if (failures == 0) {
        std::cout << "\nALL TESTS PASSED\n";
        return 0;
    }
    std::cerr << "\n" << failures << " TEST(S) FAILED\n";
    return 1;
}
