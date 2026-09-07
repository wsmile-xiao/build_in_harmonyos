// Consumer smoke test for the graaf header-only library.
// Exercises the patched public API on OHOS: graph construction, BFS reach,
// Welsh-Powell coloring (deterministic lowest-unused-color assignment) and
// Prim MST. Exits non-zero if any invariant fails.

#include <graaflib/algorithm/coloring/welsh_powell.h>
#include <graaflib/algorithm/graph_traversal/breadth_first_search.h>
#include <graaflib/algorithm/minimum_spanning_tree/prim.h>
#include <graaflib/graph.h>

#include <cstdlib>
#include <iostream>
#include <vector>

int main() {
  using graph_t = graaf::undirected_graph<int, int>;

  // Diamond graph: 4 vertices, 5 edges
  graph_t graph{};
  const auto v0{graph.add_vertex(0)};
  const auto v1{graph.add_vertex(1)};
  const auto v2{graph.add_vertex(2)};
  const auto v3{graph.add_vertex(3)};
  graph.add_edge(v0, v1, 1);
  graph.add_edge(v1, v2, 1);
  graph.add_edge(v2, v3, 1);
  graph.add_edge(v3, v0, 2);
  graph.add_edge(v1, v3, 3);

  // BFS traverse from v0 must reach all 4 vertices (collect via edge callback)
  std::unordered_set<graaf::vertex_id_t> reached{v0};
  graaf::algorithm::breadth_first_traverse(
      graph, v0,
      [&reached](const graaf::edge_id_t& edge) {
        reached.insert(edge.first);
        reached.insert(edge.second);
      });

  if (reached.size() != 4) {
    std::cerr << "FAIL: BFS reach expected 4 vertices, got " << reached.size()
              << '\n';
    return EXIT_FAILURE;
  }

  // Prim MST must contain 3 edges
  const auto mst{graaf::algorithm::prim_minimum_spanning_tree(graph, v0)};
  if (!mst.has_value() || mst->size() != 3) {
    std::cerr << "FAIL: MST expected 3 edges\n";
    return EXIT_FAILURE;
  }

  // Welsh-Powell proper coloring of K4 needs 4 distinct colors
  graaf::undirected_graph<int, int> k4{};
  const auto a{k4.add_vertex(1)};
  const auto b{k4.add_vertex(2)};
  const auto c{k4.add_vertex(3)};
  const auto d{k4.add_vertex(4)};
  k4.add_edge(a, b, 1);
  k4.add_edge(a, c, 1);
  k4.add_edge(a, d, 1);
  k4.add_edge(b, c, 1);
  k4.add_edge(b, d, 1);
  k4.add_edge(c, d, 1);

  const auto coloring{graaf::algorithm::welsh_powell_coloring(k4)};
  const std::vector<int> colors{coloring.at(a), coloring.at(b), coloring.at(c),
                                coloring.at(d)};
  for (std::size_t i{0}; i < colors.size(); ++i) {
    for (std::size_t j{i + 1}; j < colors.size(); ++j) {
      if (colors[i] == colors[j]) {
        std::cerr << "FAIL: K4 coloring not proper (" << colors[i] << " == "
                  << colors[j] << ")\n";
        return EXIT_FAILURE;
      }
    }
  }

  std::cout << "test_package OK (BFS=4, MST=3, K4 coloring proper)\n";
  return EXIT_SUCCESS;
}
