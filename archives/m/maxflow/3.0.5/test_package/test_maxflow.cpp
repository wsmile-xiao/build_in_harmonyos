// Consumer smoke test for the installed maxflow package.
//
// Mirrors the style of the upstream test_maxflow.cpp (small flow problems
// with known max-flow values and known SOURCE/SINK segmentation) but goes
// through the packaged library: find_package(maxflow) + target
// maxflow::maxflow, exercising the int and double instantiations that the
// upstream maxflow.cpp explicitly instantiates into the shared library.

#include <cmath>
#include <cstdio>
#include <maxflow.h>

using maxflow::Graph_III;
using maxflow::Graph_FFF;

static int g_failures = 0;

static void check(bool ok, const char* what) {
    if (!ok) {
        std::fprintf(stderr, "FAIL: %s\n", what);
        ++g_failures;
    }
}

/*
  Same triangle as upstream test_1:

                   SOURCE
                 /        \
               5/          \2
               /      3     \
             node0 -----> node1
               |  <-----   |
               |     4     |
               \          /
               1\        /6
                 \      /
                  SINK

  flow = 6; node0 in the SOURCE set, node1 in the SINK set.
*/
static void test_int_triangle() {
    Graph_III g(2, 1);
    g.add_node();
    g.add_node();
    g.add_tweights(0, 5, 1);
    g.add_tweights(1, 2, 6);
    g.add_edge(0, 1, 3, 4);

    const int flow = g.maxflow();
    char msg[128];
    std::snprintf(msg, sizeof(msg), "int: flow=%d, expected 6", flow);
    check(flow == 6, msg);
    check(g.what_segment(0) == Graph_III::SOURCE, "int: node0 in SOURCE set");
    check(g.what_segment(1) == Graph_III::SINK, "int: node1 in SINK set");
}

/*
  Two nodes with double capacities (exercises the Graph_FFF instantiation):

                 SOURCE
               /        \
             4.5         1.0
              |           \
            node0 --2.0--> node1
              |  <--2.0--   |
             1.0          4.5
               \          /
                 SINK (both tweights of the other side shown)

  Minimum cut is {SOURCE, node0} | {node1, SINK} with capacity
  1.0 (node0->sink) + 2.0 (node0->node1) + 1.0 (source->node1) = 4.0;
  node0 in the SOURCE set, node1 in the SINK set.
*/
static void test_double_two_nodes() {
    Graph_FFF g(2, 1);
    g.add_node();
    g.add_node();
    g.add_tweights(0, 4.5, 1.0);
    g.add_tweights(1, 1.0, 4.5);
    g.add_edge(0, 1, 2.0, 2.0);

    const double flow = g.maxflow();
    check(std::fabs(flow - 4.0) < 1e-6, "double: flow == 4.0");
    check(g.what_segment(0) == Graph_FFF::SOURCE, "double: node0 in SOURCE set");
    check(g.what_segment(1) == Graph_FFF::SINK, "double: node1 in SINK set");
}

/*
  Single node: all source capacity wins, flow equals the sink tweight.
*/
static void test_int_single_node() {
    Graph_III g(1, 1);
    const Graph_III::node_id id = g.add_node();
    g.add_tweights(id, 7, 2);
    const int flow = g.maxflow();
    char msg[128];
    std::snprintf(msg, sizeof(msg), "int single: flow=%d, expected 2", flow);
    check(flow == 2, msg);
    check(g.what_segment(id) == Graph_III::SOURCE,
          "int single: node in SOURCE set");
}

int main() {
    test_int_triangle();
    test_double_two_nodes();
    test_int_single_node();

    if (g_failures != 0) {
        std::fprintf(stderr, "%d test_package assertion(s) failed\n",
                     g_failures);
        return 1;
    }
    std::printf("test_maxflow: all assertions passed\n");
    return 0;
}
