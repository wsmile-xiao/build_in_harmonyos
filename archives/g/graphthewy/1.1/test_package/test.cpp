#include <graphthewy/GraphthewyModel.hpp>
#include <graphthewy/GraphthewyCycle.hpp>

#include <string>

int main() {
    // Directed graph with cycle detection
    graphthewy::DirectedGraph<std::string> g{"a", "b", "c"};
    g.link("a", "b");
    g.link("b", "c");
    g.link("c", "a");

    graphthewy::GraphCycle<graphthewy::DirectedGraph, std::string> gc(g);
    if (!gc.hasCycle()) {
        return 1;
    }

    // Undirected acyclic graph
    graphthewy::UndirectedGraph<int> u{1, 2, 3};
    u.link(1, 2);
    u.link(2, 3);

    graphthewy::GraphCycle<graphthewy::UndirectedGraph, int> uc(u);
    if (uc.hasCycle()) {
        return 2;
    }

    return 0;
}
