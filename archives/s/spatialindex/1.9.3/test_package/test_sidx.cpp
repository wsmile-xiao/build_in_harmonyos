// Consumer test for libspatialindex: build an in-memory R*-tree, insert
// points, run a range query and verify the result set.
#include <spatialindex/SpatialIndex.h>
#include <cstdio>
#include <memory>
#include <vector>

using namespace SpatialIndex;

class Visitor : public IVisitor {
public:
    void visitNode(const INode &) override {}
    void visitData(const IData &d) override {
        m_ids.push_back(d.getIdentifier());
    }
    void visitData(std::vector<const IData *> &) override {}
    std::vector<int64_t> m_ids;
};

int main(void)
{
    try {
        std::unique_ptr<IStorageManager> stor(
            StorageManager::createNewMemoryStorageManager());
        id_type indexId = 0;
        std::unique_ptr<ISpatialIndex> tree(
            RTree::createNewRTree(*stor, 0.7, 100, 100, 2,
                                  SpatialIndex::RTree::RV_RSTAR,
                                  indexId));
        // insert 100 points on a diagonal
        for (int64_t i = 0; i < 100; ++i) {
            double lo[2] = {(double)i, (double)i};
            double hi[2] = {(double)i + 0.5, (double)i + 0.5};
            Region r(lo, hi, 2);
            std::unique_ptr<IShape> shape(r.clone());
            tree->insertData(0, nullptr, *shape, i);
        }
        // range query over the middle of the diagonal
        Visitor vis;
        double qlo[2] = {25.0, 25.0};
        double qhi[2] = {75.0, 75.0};
        Region q(qlo, qhi, 2);
        tree->intersectsWithQuery(q, vis);
        if (vis.m_ids.size() != 51) {
            std::fprintf(stderr,
                         "FAIL: expected 51 hits, got %zu\n",
                         vis.m_ids.size());
            return 1;
        }
        std::printf("spatialindex consumer test: PASS (%zu hits)\n",
                    vis.m_ids.size());
        return 0;
    } catch (Tools::Exception &e) {
        std::fprintf(stderr, "FAIL: exception: %s\n", e.what().c_str());
        return 1;
    }
}
