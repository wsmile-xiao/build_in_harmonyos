#include <array>
#include <sstream>
#include <string>

#include <boost/pending/disjoint_sets.hpp>
#include <boost/graph/adjacency_list.hpp>
#include <boost/graph/graphviz.hpp>

int main() {
    const std::array<std::size_t, 6> elements{0, 1, 2, 3, 4, 5};
    boost::disjoint_sets_with_storage<> sets(elements.size());
    for (const auto element : elements) {
        sets.make_set(element);
    }

    int failures = sets.count_sets(elements.begin(), elements.end()) != 6;
    sets.union_set(0, 1);
    failures += sets.find_set(0) != sets.find_set(1);
    failures += sets.find_set(0) == sets.find_set(2);
    sets.union_set(2, 3);
    failures += sets.count_sets(elements.begin(), elements.end()) != 4;
    sets.union_set(1, 2);
    failures += sets.count_sets(elements.begin(), elements.end()) != 3;

    using Graph = boost::adjacency_list<
        boost::vecS,
        boost::vecS,
        boost::undirectedS,
        boost::property<boost::vertex_name_t, std::string>>;
    Graph graph;
    boost::dynamic_properties properties;
    properties.property("node_id", boost::get(boost::vertex_name, graph));
    std::istringstream dot("graph G { alpha -- beta; beta -- gamma; }");
    failures += !boost::read_graphviz(dot, graph, properties, "node_id");
    failures += boost::num_vertices(graph) != 3;
    failures += boost::num_edges(graph) != 2;
    return failures;
}
