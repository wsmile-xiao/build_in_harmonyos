// test.cpp — lttoolbox API smoke test
//
// Verifies that the lttoolbox headers are accessible and the library
// links correctly. We instantiate a Transducer and Alphabet — the core
// data structures used by lt-print and other lttoolbox tools.
#include <lttoolbox/transducer.h>
#include <lttoolbox/alphabet.h>
#include <lttoolbox/entry_token.h>
#include <cstdio>
#include <cstdint>

int main(void)
{
    // Test 1: Alphabet instantiation and size
    Alphabet alphabet;
    int32_t sz = alphabet.size();
    (void)sz;  // size() returns 0 for a fresh alphabet

    // Test 2: Transducer instantiation
    Transducer transducer;
    int initial = transducer.getInitial();
    if (initial < 0) {
        fprintf(stderr, "FAIL: initial state should be >= 0, got %d\n", initial);
        return 1;
    }

    // Test 3: Mark a state final and verify
    transducer.setFinal(initial);
    if (!transducer.isFinal(initial)) {
        fprintf(stderr, "FAIL: state not marked final after setFinal\n");
        return 1;
    }

    // Test 4: Verify getFinals returns the expected map
    auto finals = transducer.getFinals();
    if (finals.find(initial) == finals.end()) {
        fprintf(stderr, "FAIL: initial state not in finals map\n");
        return 1;
    }

    printf("OK: lttoolbox Transducer+Alphabet API smoke test passed\n");
    return 0;
}
