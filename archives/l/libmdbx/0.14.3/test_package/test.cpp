#include <mdbx.h++>

#include <cstdio>
#include <exception>

static int passed;
static int failed;

static void check(bool condition, const char *label) {
    if (condition) {
        ++passed;
        std::printf("PASS: %s\n", label);
    } else {
        ++failed;
        std::fprintf(stderr, "FAIL: %s\n", label);
    }
}

int main() {
    const char *database_path = "libmdbx_cpp_consumer.mdbx";
    try {
        (void)mdbx::env::remove(database_path);
        {
            mdbx::env::operate_parameters operation(4);
            mdbx::env_managed env(database_path, mdbx::env_managed::create_parameters(),
                                  operation);
            check(static_cast<bool>(env), "create C++ environment");

            {
                auto txn = env.start_write();
                auto map = txn.create_map("data", mdbx::key_mode::usual, mdbx::value_mode::single);
                check(static_cast<bool>(map), "create named map");
                txn.insert(map, mdbx::slice("alpha"), mdbx::slice("one"));
                check(true, "insert C++ key and value");
                txn.commit();
                check(true, "commit C++ transaction");
            }

            {
                auto txn = env.start_read();
                auto map = txn.open_map("data");
                check(static_cast<bool>(map), "open named map");
                const auto found = txn.get(map, mdbx::slice("alpha"));
                check(found == mdbx::slice("one"), "read C++ value");
                const auto fallback = txn.get(map, mdbx::slice("missing"), mdbx::slice("fallback"));
                check(fallback == mdbx::slice("fallback"), "handle missing C++ key");
            }
        }
        check(mdbx::env::remove(database_path), "remove C++ database");
    } catch (const std::exception &error) {
        ++failed;
        std::fprintf(stderr, "C++ exception: %s\n", error.what());
    }

    std::printf("libmdbx C++ consumer: %d passed, %d failed\n", passed, failed);
    return failed == 0 ? 0 : 1;
}
