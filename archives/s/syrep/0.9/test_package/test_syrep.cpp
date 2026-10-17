// syrep test_package: exercise the packaged binary end-to-end.
// Verifies the built syrep tool actually works on the target platform:
// version smoke + a real update/diff/makepatch/merge round-trip using
// temp directories (PATH from the conanrun environment).
#include <cstdio>
#include <cstdlib>
#include <string>

namespace {

int run(const std::string &cmd)
{
    int rc = std::system(cmd.c_str());
    if (rc != 0)
        std::printf("FAILED: %s (rc=%d)\n", cmd.c_str(), rc);
    return rc;
}

} // namespace

int main()
{
    const char *tmp = std::getenv("TMPDIR");
    std::string base = (tmp ? tmp : "/tmp");
    base += "/syrep-test-XXXXXX";

    // mkdtemp inside TMPDIR (writable per conanrun env); record dir to a
    // file inside TMPDIR as well — /tmp is read-only on OHOS (E002)
    std::string dirfile = std::string(tmp ? tmp : ".") + "/syrep-test-dir.txt";
    if (run("d=$(mktemp -d '" + base + "') && echo $d > '" + dirfile + "'") != 0)
        return 1;
    FILE *f = std::fopen(dirfile.c_str(), "r");
    char buf[512] = {0};
    if (!f || !std::fgets(buf, sizeof(buf), f))
        return 1;
    std::fclose(f);
    std::string dir(buf);
    while (!dir.empty() && (dir.back() == '\n' || dir.back() == '\r'))
        dir.pop_back();

    const std::string a = dir + "/a", b = dir + "/b";
    const std::string patch = dir + "/p.syrep";

    // 1. version smoke test: binary runs and reports itself
    if (run("syrep --version >/dev/null") != 0)
        return 1;

    // 2. real workflow: populate repo A, snapshot it
    if (run("mkdir -p '" + a + "' '" + b + "'") != 0)
        return 1;
    if (run("printf hello > '" + a + "/f1.txt' && printf world > '" + a + "/f2.txt'") != 0)
        return 1;
    if (run("syrep --update '" + a + "' >/dev/null 2>&1") != 0)
        return 1;
    if (run("test -f '" + a + "/.syrep/current.syrep'") != 0)
        return 1;

    // 3. makepatch A -> B, merge into B, verify contents propagated
    // (makepatch requires both repos to have snapshots: update B as well)
    if (run("syrep --update '" + b + "' >/dev/null 2>&1") != 0)
        return 1;
    if (run("syrep '" + a + "' '" + b + "' --makepatch -o '" + patch + "' >/dev/null 2>&1") != 0)
        return 1;
    if (run("syrep --merge '" + patch + "' '" + b + "' >/dev/null 2>&1") != 0)
        return 1;
    if (run("test \"$(cat '" + b + "/f1.txt')\" = hello && test \"$(cat '" + b + "/f2.txt')\" = world") != 0)
        return 1;

    std::printf("syrep 0.9 test passed: update/makepatch/merge round-trip OK\n");
    return 0;
}
