// Consumer contract test for the OpenDBX 1.4.6 C++ API (libopendbxplus).
//
// No database server is needed: the checks cover Exception value semantics
// and the documented throws-on-unusable-handle behavior of Conn. Each CHECK
// prints PASS/FAIL; the summary line carries the exact counts.
#include <cstdio>
#include <string>

#include <opendbx/api>

static int passed = 0;
static int failed = 0;

#define CHECK(cond, name)                                                     \
    do {                                                                      \
        if (cond) {                                                           \
            std::printf("PASS: %s\n", name);                                  \
            ++passed;                                                         \
        } else {                                                              \
            std::printf("FAIL: %s\n", name);                                  \
            ++failed;                                                         \
        }                                                                     \
    } while (0)

int main()
{
    /* Exception carries message, code and severity. */
    OpenDBX::Exception err(std::string("probe"), -ODBX_ERR_NOTEXIST, -1);
    CHECK(err.getCode() == -ODBX_ERR_NOTEXIST, "exception-code");
    CHECK(err.getType() == -1, "exception-type");
    CHECK(std::string(err.what()) == "probe", "exception-what");

    /* A default-constructed Conn has no implementation and must throw
     * ODBX_ERR_HANDLE on use. */
    OpenDBX::Conn conn;
    bool threw = false;
    int code = 0;
    try {
        conn.getCapability(ODBX_CAP_BASIC);
    } catch (const OpenDBX::Exception& e) {
        threw = true;
        code = e.getCode();
    }
    CHECK(threw, "default-conn-capability-throws");
    CHECK(code == -ODBX_ERR_HANDLE, "default-conn-error-handle");

    threw = false;
    try {
        conn.bind("db", "user", "cred", ODBX_BIND_SIMPLE);
    } catch (const OpenDBX::Exception&) {
        threw = true;
    }
    CHECK(threw, "default-conn-bind-throws");

    /* Unknown backend name propagates ODBX_ERR_NOTEXIST through C++. */
    threw = false;
    code = 0;
    try {
        OpenDBX::Conn bad("opendbx_hmos_probe_backend", "", "");
    } catch (const OpenDBX::Exception& e) {
        threw = true;
        code = e.getCode();
    }
    CHECK(threw, "unknown-backend-conn-throws");
    CHECK(code == -ODBX_ERR_NOTEXIST, "unknown-backend-notexist");

    std::printf("test_opendbxplus: %d passed, %d failed\n", passed, failed);
    return failed ? 1 : 0;
}
