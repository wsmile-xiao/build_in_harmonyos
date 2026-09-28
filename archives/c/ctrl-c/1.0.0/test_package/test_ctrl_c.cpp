/*
 * Consumer test for ctrl-c 1.0.0 (HarmonyOS PC / aarch64, clang 15, libc++).
 *
 * Upstream ships only an *interactive* example (test/main.cpp: "Press Ctrl+C
 * 3 times"). This consumer test reuses the same upstream API surface but drives
 * SIGINT programmatically so it can run non-interactively in `conan create`
 * and in CI:
 *
 *   case0_packaged_header_fingerprint — the delivered ctrl-c.h is the upstream
 *                                     1.0.0 header (include guard) and its
 *                                     published constants have stable values
 *   case1_basic_signal_delivery     — SetCtrlCHandler + one raise(SIGINT)
 *   case2_repeated_delivery         — 3 SIGINT in total (upstream kMaxCatches parity)
 *   case3_lifo_and_stop_propagation — two handlers, last registered runs first,
 *                                     returning true stops propagation
 *   case4_reset_single_handler      — ResetCtrlCHandler(id) removes only that one
 *   case5_reset_all_and_reinstall   — empty list restores SIG_DFL (verified with
 *                                     a sigaction query), re-register reinstalls
 *
 * 6 cases / 20 assertions. Registered handlers only touch plain data: the
 * library invokes them while holding its internal mutex, and upstream documents
 * that calling Set/ResetCtrlCHandler from inside a handler deadlocks.
 */
#include <ctrl-c.h>

#include <csignal>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

// The package must deliver the upstream ctrl-c.h unchanged; the include guard
// is upstream's fingerprint (single-file package: the header *is* the product).
#ifndef CTRLC_H_EVGENY_KISLOV_20200401
#error "packaged ctrl-c.h is not the upstream ctrl-c 1.0.0 header"
#endif

namespace {

int check_failures = 0;
int failed_cases = 0;
int case_failed = 0;
const char *case_name = "";

void begin_case(const char *name) {
    case_name = name;
    case_failed = 0;
}

void end_case() {
    std::printf("%s: %s\n", case_name, case_failed == 0 ? "PASS" : "FAIL");
    if (case_failed != 0) {
        ++failed_cases;
    }
}

#define CHECK(cond)                                                         \
    do {                                                                    \
        if (!(cond)) {                                                      \
            std::printf("  CHECK failed: %s (line %d)\n", #cond, __LINE__); \
            ++case_failed;                                                  \
            ++check_failures;                                               \
        }                                                                   \
    } while (0)

}  // namespace

int main() {
    // case 0: the packaged header/constants are the upstream 1.0.0 ones.
    begin_case("case0_packaged_header_fingerprint");
    CHECK(CtrlCLibrary::kErrorID == 0u);
    CHECK(CtrlCLibrary::kCtrlCSignal == 0);
    end_case();

    // case 1: a registered handler receives one SIGINT raised in-process.
    begin_case("case1_basic_signal_delivery");
    int caught = 0;
    enum CtrlCLibrary::CtrlSignal last_event = CtrlCLibrary::kCtrlCSignal;
    unsigned int id1 = CtrlCLibrary::SetCtrlCHandler(
        [&caught, &last_event](enum CtrlCLibrary::CtrlSignal event) -> bool {
            last_event = event;
            ++caught;
            return true;
        });
    CHECK(id1 != CtrlCLibrary::kErrorID);
    std::raise(SIGINT);
    CHECK(caught == 1);
    CHECK(last_event == CtrlCLibrary::kCtrlCSignal);
    end_case();

    // case 2: repeated delivery keeps counting (3 total, upstream parity).
    // The three SIGINTs come from the case-1 handler, so release it again
    // afterwards: the library only hands SIGINT back to SIG_DFL once its
    // handler list is empty (verified in case 5).
    begin_case("case2_repeated_delivery");
    std::raise(SIGINT);
    CHECK(caught == 2);
    std::raise(SIGINT);
    CHECK(caught == 3);
    CtrlCLibrary::ResetCtrlCHandler(id1);
    end_case();

    // case 3: handlers are LIFO; returning true stops propagation.
    begin_case("case3_lifo_and_stop_propagation");
    std::vector<std::string> order;
    unsigned int id_a = CtrlCLibrary::SetCtrlCHandler(
        [&order](enum CtrlCLibrary::CtrlSignal) -> bool {
            order.push_back("A");
            return false;
        });
    unsigned int id_b = CtrlCLibrary::SetCtrlCHandler(
        [&order](enum CtrlCLibrary::CtrlSignal) -> bool {
            order.push_back("B");
            return true;
        });
    CHECK(id_a != CtrlCLibrary::kErrorID);
    CHECK(id_b != CtrlCLibrary::kErrorID);
    CHECK(id_a != id_b);
    std::raise(SIGINT);
    CHECK(order == std::vector<std::string>{"B"});
    end_case();

    // case 4: resetting one handler leaves the earlier one installed.
    begin_case("case4_reset_single_handler");
    CtrlCLibrary::ResetCtrlCHandler(id_b);
    order.clear();
    std::raise(SIGINT);
    CHECK(order == std::vector<std::string>{"A"});
    end_case();

    // case 5: an empty list hands SIGINT back to SIG_DFL, re-registering
    // restores the catcher. State is inspected with sigaction() instead of
    // delivering a signal while SIG_DFL is installed (that would terminate the
    // test process).
    begin_case("case5_reset_all_and_reinstall");
    CtrlCLibrary::ResetCtrlCHandler(id_a);
    struct sigaction query;
    std::memset(&query, 0, sizeof(query));
    CHECK(sigaction(SIGINT, nullptr, &query) == 0);
    CHECK(query.sa_handler == SIG_DFL);

    int caught_c = 0;
    unsigned int id_c = CtrlCLibrary::SetCtrlCHandler(
        [&caught_c](enum CtrlCLibrary::CtrlSignal) -> bool {
            ++caught_c;
            return true;
        });
    CHECK(id_c != CtrlCLibrary::kErrorID);
    std::memset(&query, 0, sizeof(query));
    CHECK(sigaction(SIGINT, nullptr, &query) == 0);
    CHECK(query.sa_handler != SIG_DFL);

    std::raise(SIGINT);
    CHECK(caught_c == 1);

    CtrlCLibrary::ResetCtrlCHandler(id_c);
    std::memset(&query, 0, sizeof(query));
    CHECK(sigaction(SIGINT, nullptr, &query) == 0);
    CHECK(query.sa_handler == SIG_DFL);
    end_case();

    std::printf("cases=6 failed_cases=%d failed_checks=%d\n", failed_cases,
                check_failures);
    return (failed_cases == 0 && check_failures == 0) ? 0 : 1;
}
