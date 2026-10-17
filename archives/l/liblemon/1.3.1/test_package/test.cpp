#include <cstdlib>
#include <iostream>

#include <lemon/bfs.h>
#include <lemon/core.h>
#include <lemon/list_graph.h>
#include <lemon/random.h>

int main() {
  lemon::ListDigraph graph;
  const lemon::ListDigraph::Node source = graph.addNode();
  const lemon::ListDigraph::Node middle = graph.addNode();
  const lemon::ListDigraph::Node target = graph.addNode();
  graph.addArc(source, middle);
  graph.addArc(middle, target);

  if (lemon::countNodes(graph) != 3) {
    std::cerr << "unexpected node count" << std::endl;
    return EXIT_FAILURE;
  }
  if (lemon::countArcs(graph) != 2) {
    std::cerr << "unexpected arc count" << std::endl;
    return EXIT_FAILURE;
  }

  lemon::Bfs<lemon::ListDigraph> bfs(graph);
  bfs.run(source);
  if (!bfs.reached(target)) {
    std::cerr << "BFS did not reach target" << std::endl;
    return EXIT_FAILURE;
  }
  if (bfs.dist(target) != 2) {
    std::cerr << "unexpected BFS distance" << std::endl;
    return EXIT_FAILURE;
  }

  lemon::rnd.seed(20260906U);
  const unsigned int first = lemon::rnd[1000000U];
  lemon::rnd.seed(20260906U);
  const unsigned int second = lemon::rnd[1000000U];
  if (first != second) {
    std::cerr << "global random generator is not repeatable after reseeding"
              << std::endl;
    return EXIT_FAILURE;
  }
  if (first >= 1000000U) {
    std::cerr << "global random generator exceeded the requested range"
              << std::endl;
    return EXIT_FAILURE;
  }

  std::cout << "liblemon consumer test passed" << std::endl;
  return EXIT_SUCCESS;
}

