// test_package for pcrecpp 8.45 — exercises the C++ wrapper API (R34).
// Uses pcrecpp::RE (compile + full/partial match + capture) and
// pcrecpp::StringPiece via the pcrecpp header.
#include <pcrecpp.h>
#include <pcre_stringpiece.h>
#include <cstdio>
#include <string>

int main() {
    // 1) Full match with capture group
    pcrecpp::RE re("(\\d+)-(\\d+)");
    std::string left, right;
    if (!re.FullMatch("123-456", &left, &right)) {
        printf("pcrecpp test: FullMatch FAILED\n");
        return 1;
    }
    if (left != "123" || right != "456") {
        printf("pcrecpp test: capture mismatch ('%s'/'%s')\n", left.c_str(), right.c_str());
        return 1;
    }
    printf("pcrecpp test: FullMatch ok (left='%s', right='%s')\n", left.c_str(), right.c_str());

    // 2) Partial match
    pcrecpp::RE re2("world");
    if (!re2.PartialMatch("hello world")) {
        printf("pcrecpp test: PartialMatch FAILED\n");
        return 1;
    }
    printf("pcrecpp test: PartialMatch ok\n");

    // 3) StringPiece usage
    pcrecpp::StringPiece sp("a=1&b=2");
    pcrecpp::RE re3("b=(\\d+)");
    int bval = 0;
    if (!re3.FindAndConsume(&sp, &bval) || bval != 2) {
        printf("pcrecpp test: FindAndConsume FAILED\n");
        return 1;
    }
    printf("pcrecpp test: FindAndConsume ok (b=%d)\n", bval);

    // 4) Error handling: invalid pattern
    pcrecpp::RE re4("(");
    if (re4.error().empty()) {
        printf("pcrecpp test: error() should be non-empty for bad pattern\n");
        return 1;
    }
    printf("pcrecpp test: error handling ok ('%s')\n", re4.error().c_str());

    // 5) Options: case-insensitive matching
    pcrecpp::RE_Options opts;
    opts.set_caseless(true);
    pcrecpp::RE re5("abc", opts);
    if (!re5.PartialMatch("XXABCyy")) {
        printf("pcrecpp test: caseless option FAILED\n");
        return 1;
    }
    printf("pcrecpp test: options ok\n");

    printf("pcrecpp test: ALL PASS\n");
    return 0;
}
