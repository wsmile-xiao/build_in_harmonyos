// test_mcqd.cpp — consumer test for mcqd 1.0.0 header-only library.
// Builds a small 4-node graph with a known maximum clique of size 3
// (triangle 0-1-2 plus node 3 attached only to 0) and exercises both
// Maxclique::mcq() and Maxclique::mcqdyn(). Each CHECK prints PASS/FAIL
// and increments the pass counter; exit code is non-zero on any failure.
#include <iostream>
#include "mcqd.h"

static int g_passed = 0;
static int g_failed = 0;

#define CHECK(cond, msg) do { \
    if (cond) { \
        std::cout << "CHECK PASS: " << msg << std::endl; \
        g_passed++; \
    } else { \
        std::cout << "CHECK FAIL: " << msg << std::endl; \
        g_failed++; \
    } \
} while (0)

static bool** make_graph(int n) {
    bool** conn = new bool*[n];
    for (int i = 0; i < n; i++) {
        conn[i] = new bool[n];
        for (int j = 0; j < n; j++) conn[i][j] = false;
    }
    return conn;
}

static void free_graph(bool** conn, int n) {
    for (int i = 0; i < n; i++) delete[] conn[i];
    delete[] conn;
}

static void link(bool** conn, int a, int b) {
    conn[a][b] = true;
    conn[b][a] = true;
}

static bool clique_valid(bool** conn, int* clique, int size) {
    for (int i = 0; i < size; i++) {
        for (int j = i + 1; j < size; j++) {
            if (!conn[clique[i]][clique[j]]) return false;
        }
    }
    return true;
}

int main() {
    const int n = 4;
    bool** conn = make_graph(n);
    link(conn, 0, 1);
    link(conn, 1, 2);
    link(conn, 0, 2);
    link(conn, 0, 3);

    // Scenario 1: classic branch-and-bound mcq().
    {
        Maxclique m((const bool* const*)conn, n);
        int* qmax = nullptr;
        int qsize = 0;
        m.mcq(qmax, qsize);
        CHECK(qsize == 3, "mcq() finds maximum clique of size 3 on triangle graph");
        CHECK(qmax != nullptr && clique_valid(conn, qmax, qsize), "mcq() clique is fully connected in the input graph");
        CHECK(m.steps() > 0, "mcq() advances the internal step counter");
        delete[] qmax;
    }

    // Scenario 2: dynamic-ordering mcqdyn().
    {
        Maxclique md((const bool* const*)conn, n, 0.025f);
        int* qmax = nullptr;
        int qsize = 0;
        md.mcqdyn(qmax, qsize);
        CHECK(qsize == 3, "mcqdyn() finds maximum clique of size 3 on triangle graph");
        CHECK(qmax != nullptr && clique_valid(conn, qmax, qsize), "mcqdyn() clique is fully connected in the input graph");
        CHECK(md.steps() > 0, "mcqdyn() advances the internal step counter");
        delete[] qmax;
    }

    free_graph(conn, n);

    std::cout << "SUMMARY passed=" << g_passed << " failed=" << g_failed << std::endl;
    if (g_failed != 0 || g_passed != 6) {
        std::cerr << "FAIL: expected 6/6 checks to pass" << std::endl;
        return 1;
    }
    std::cout << "PASS: mcqd header-only library and both Maxclique APIs verified" << std::endl;
    return 0;
}
