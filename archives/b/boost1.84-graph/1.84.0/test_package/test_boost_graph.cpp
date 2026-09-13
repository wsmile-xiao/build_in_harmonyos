// test_package/test_boost_graph.cpp — boost1.84-graph 1.84.0 L1 smoke test.
// Exercises Boost.Graph header-only APIs (adjacency_list/BFS/DFS/Dijkstra/
// topological sort) plus the compiled libboost_graph.a
// (read_graphviz / read_graphml / write_graphml round-trip).
#include <boost/graph/adjacency_list.hpp>
#include <boost/graph/breadth_first_search.hpp>
#include <boost/graph/depth_first_search.hpp>
#include <boost/graph/dijkstra_shortest_paths.hpp>
#include <boost/graph/topological_sort.hpp>
#include <boost/graph/graphviz.hpp>
#include <boost/graph/graphml.hpp>
#include <boost/property_map/dynamic_property_map.hpp>
#include <iostream>
#include <sstream>
#include <vector>

typedef boost::adjacency_list<boost::vecS, boost::vecS, boost::directedS,
    boost::property<boost::vertex_name_t, std::string> > digraph_t;

// 计数 visitor：BFS/DFS 访问顶点时自增（header-only API 冒烟）
// BFS 与 DFS 的事件集不同（BFS 用 default_bfs_visitor，DFS 用
// default_dfs_visitor），分别派生两个计数 visitor，各自覆写 discover_vertex
struct bfs_counter : boost::default_bfs_visitor {
    bfs_counter(int* cnt) : count(cnt) {}
    template < typename Vertex, typename Graph >
    void discover_vertex(Vertex, const Graph&) const { ++(*count); }
    int* count;
};

struct dfs_counter : boost::default_dfs_visitor {
    dfs_counter(int* cnt) : count(cnt) {}
    template < typename Vertex, typename Graph >
    void discover_vertex(Vertex, const Graph&) const { ++(*count); }
    int* count;
};

int main() {
    int checks = 0;

    // 1. adjacency_list 构造与顶点/边计数
    digraph_t g;
    boost::add_edge(0, 1, g);
    boost::add_edge(1, 2, g);
    boost::add_edge(2, 0, g);
    boost::add_edge(2, 3, g);
    if (boost::num_vertices(g) != 4 || boost::num_edges(g) != 4) {
        std::cerr << "adjacency_list: vertex/edge count mismatch" << std::endl;
        return 1;
    }
    ++checks;

    // 2. BFS（on_discover_vertex 计数）
    int bfs_count = 0;
    boost::breadth_first_search(g, 0,
        boost::visitor(bfs_counter(&bfs_count)));
    if (bfs_count != 4) {
        std::cerr << "bfs: visited " << bfs_count << ", expected 4" << std::endl;
        return 1;
    }
    ++checks;

    // 3. DFS（on_discover_vertex 计数）
    int dfs_count = 0;
    boost::depth_first_search(g,
        boost::visitor(dfs_counter(&dfs_count)));
    if (dfs_count != 4) {
        std::cerr << "dfs: visited " << dfs_count << ", expected 4" << std::endl;
        return 1;
    }
    ++checks;

    // 4. Dijkstra 最短路径
    typedef boost::adjacency_list<boost::vecS, boost::vecS, boost::undirectedS,
        boost::no_property, boost::property<boost::edge_weight_t, int> > wgraph_t;
    wgraph_t wg;
    boost::add_edge(0, 1, 4, wg);
    boost::add_edge(1, 2, 3, wg);
    boost::add_edge(0, 2, 10, wg);
    std::vector<int> dist(3);
    boost::dijkstra_shortest_paths(wg, 0,
        boost::distance_map(boost::make_iterator_property_map(
            dist.begin(), get(boost::vertex_index, wg))));
    if (dist[2] != 7) {  // 0->1->2 = 4+3，短于直连 10
        std::cerr << "dijkstra: dist[2]=" << dist[2] << ", expected 7" << std::endl;
        return 1;
    }
    ++checks;
    std::cout << "dijkstra: 0->2 shortest path = " << dist[2] << " OK" << std::endl;

    // 5. topological_sort（需 DAG——用无环图 a0->a1->a2->a3）
    digraph_t dag;
    boost::add_edge(0, 1, dag);
    boost::add_edge(1, 2, dag);
    boost::add_edge(2, 3, dag);
    std::vector<int> topo;
    boost::topological_sort(dag, std::back_inserter(topo));
    if (topo.size() != 4) {
        std::cerr << "topological_sort: expected 4, got " << topo.size() << std::endl;
        return 1;
    }
    ++checks;

    // 6. read_graphviz（编译库 libboost_graph.a 的 DOT 解析路径）
    digraph_t vg;
    std::istringstream iss("digraph G { a -> b; b -> c; }");
    boost::dynamic_properties dp;
    dp.property("node_id", get(boost::vertex_name, vg));
    try {
        boost::read_graphviz(iss, vg, dp, "node_id");
    } catch (const std::exception& e) {
        std::cerr << "read_graphviz exception: " << e.what() << std::endl;
        return 1;
    }
    if (boost::num_vertices(vg) != 3 || boost::num_edges(vg) != 2) {
        std::cerr << "read_graphviz: graph size mismatch ("
                  << boost::num_vertices(vg) << "v/" << boost::num_edges(vg) << "e)"
                  << std::endl;
        return 1;
    }
    ++checks;

    // 7. write_graphviz
    std::ostringstream oss;
    boost::write_graphviz(oss, vg);
    if (oss.str().find("digraph") == std::string::npos) {
        std::cerr << "write_graphviz: output missing digraph header" << std::endl;
        return 1;
    }
    ++checks;

    // 8. write_graphml + read_graphml 往返（graphml.cpp 编译路径）
    std::ostringstream xml_out;
    boost::dynamic_properties dp2;
    dp2.property("node_id", get(boost::vertex_name, vg));
    boost::write_graphml(xml_out, vg, dp2, true);
    if (xml_out.str().find("<graph") == std::string::npos) {
        std::cerr << "write_graphml: output missing <graph> element" << std::endl;
        return 1;
    }
    ++checks;
    digraph_t vg2;
    boost::dynamic_properties dp3;
    dp3.property("node_id", get(boost::vertex_name, vg2));
    std::istringstream xml_in(xml_out.str());
    try {
        boost::read_graphml(xml_in, vg2, dp3);
    } catch (const std::exception& e) {
        std::cerr << "read_graphml exception: " << e.what() << std::endl;
        return 1;
    }
    if (boost::num_vertices(vg2) != 3 || boost::num_edges(vg2) != 2) {
        std::cerr << "read_graphml round-trip mismatch (" << boost::num_vertices(vg2)
                  << "v/" << boost::num_edges(vg2) << "e)" << std::endl;
        return 1;
    }
    ++checks;
    std::cout << "graphml round-trip: " << boost::num_vertices(vg2) << "v/"
              << boost::num_edges(vg2) << "e OK" << std::endl;

    std::cout << "test_boost_graph: all " << checks << " checks passed" << std::endl;
    return 0;
}
