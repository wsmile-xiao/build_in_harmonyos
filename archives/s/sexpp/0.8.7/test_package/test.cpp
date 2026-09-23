// test.cpp — consumer test for sexpp/0.8.7
//
// Links against the packaged libsexpp and drives the public API declared in
// <sexpp/sexp.h>: scan an S-expression from a std::istream and print it back
// in canonical (length-prefixed) form, then check the exact bytes. Canonical
// form is the format used for hashing and transmission, so an exact-string
// comparison is a meaningful end-to-end assertion rather than a print stub.
#include <iostream>
#include <sstream>
#include <string>

#include <sexpp/sexp.h>

static int failures = 0;

static void check(bool ok, const char *what)
{
    if (ok) {
        std::cout << "ok   : " << what << std::endl;
    } else {
        std::cerr << "FAIL : " << what << std::endl;
        ++failures;
    }
}

// Scan the first S-expression in `text` and return its canonical rendering.
static std::string canonicalise(const std::string &text, bool *parsed)
{
    std::istringstream in(text, std::ios_base::binary);
    sexp::sexp_input_stream_t is(&in);
    auto obj = is.set_byte_size(8)->get_char()->scan_object();
    *parsed = (obj != nullptr);
    if (!obj) {
        return std::string();
    }
    std::ostringstream out(std::ios_base::binary);
    sexp::sexp_output_stream_t os(&out);
    os.print_canonical(obj);
    return out.str();
}

int main()
{
    bool parsed = false;

    // 1) default scanning byte size is 8 (set by the constructor via set_input)
    {
        std::istringstream in("(a)", std::ios_base::binary);
        sexp::sexp_input_stream_t is(&in);
        check(is.get_byte_size() == 8, "default scan byte size is 8");
    }

    // 2) a nested list is scanned and re-printed in canonical form
    {
        const std::string got = canonicalise("(hello (world test))", &parsed);
        check(parsed, "scan_object() parses a nested list");
        std::cout << "     canonical = " << got << std::endl;
        check(got == "(5:hello(5:world4:test))",
              "canonical output is exactly length-prefixed");
    }

    // 3) a bare quoted string becomes a single length-prefixed atom
    {
        const std::string got = canonicalise("\"abc\"", &parsed);
        check(parsed, "scan_object() parses a bare quoted string");
        check(got == "3:abc", "quoted string canonicalises to 3:abc");
    }

    // 4) a token keeps its characters and gains a length prefix
    {
        const std::string got = canonicalise("(a-b.c)", &parsed);
        check(parsed, "scan_object() parses a token with punctuation");
        check(got == "(5:a-b.c)", "token canonicalises to (5:a-b.c)");
    }

    // 5) an empty stream triggers EOF error (upstream throws; we verify it)
    {
        std::istringstream in("", std::ios_base::binary);
        sexp::sexp_input_stream_t is(&in);
        bool threw = false;
        try {
            is.set_byte_size(8)->get_char()->scan_object();
        } catch (const sexp::sexp_exception_t &) {
            threw = true;
        }
        check(threw, "scan_object() on an empty stream throws sexp_exception_t");
    }

    // 6) the public simple-string comparison helper works as documented
    {
        // octet_t is uint8_t, so the ctor needs an octet buffer, not a char*
        const sexp::octet_t abc[] = {'a', 'b', 'c', 0};
        sexp::sexp_simple_string_t s(abc);
        check(s == "abc", "sexp_simple_string_t == const char* matches");
        check(s != "abd", "sexp_simple_string_t != const char* differs");
    }

    if (failures != 0) {
        std::cerr << failures << " consumer assertion(s) failed" << std::endl;
        return 1;
    }
    std::cout << "ALL CONSUMER CHECKS PASSED" << std::endl;
    return 0;
}
