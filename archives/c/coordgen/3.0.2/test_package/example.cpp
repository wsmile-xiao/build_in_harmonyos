#include <cmath>
#include <cstdio>

#include <coordgen/sketcherMinimizer.h>

// 真实消费者：只用安装后的公开 API（include/coordgen/*.h）。程序化构建
// 苯环（6 C，Kekulé 交替键序 1/2），经 sketcherMinimizer 生成 2D 坐标，
// 校验原子/键计数、坐标有限性、键长合理且近正六边形（编译期内嵌模板
// 识别生效，USE_MAEPARSER=OFF 路径），以及原子位置互异。
int main() {
    int checks = 0;
    int failures = 0;
    #define CHECK(cond, msg) do { \
        ++checks; \
        if (!(cond)) { std::printf("FAIL: %s\n", msg); ++failures; } \
    } while (0)

    sketcherMinimizer minimizer;
    auto* mol = new sketcherMinimizerMolecule();

    sketcherMinimizerAtom* atoms[6];
    for (int i = 0; i < 6; ++i) {
        atoms[i] = mol->addNewAtom();
        atoms[i]->setAtomicNumber(6);
    }
    for (int i = 0; i < 6; ++i) {
        auto* bond = mol->addNewBond(atoms[i], atoms[(i + 1) % 6]);
        bond->setBondOrder(i % 2 == 0 ? 1 : 2);
    }

    CHECK(mol->getAtoms().size() == 6, "atom count == 6");
    CHECK(mol->getBonds().size() == 6, "bond count == 6");

    // minimizer takes ownership of mol (same objects stay reachable).
    minimizer.initialize(mol);
    minimizer.runGenerateCoordinates();

    double minLen = 1e9;
    double maxLen = 0.0;
    for (auto& bond : mol->getBonds()) {
        const auto& s = bond->getStartAtom()->getCoordinates();
        const auto& e = bond->getEndAtom()->getCoordinates();
        double dx = static_cast<double>(s.x()) - static_cast<double>(e.x());
        double dy = static_cast<double>(s.y()) - static_cast<double>(e.y());
        CHECK(std::isfinite(dx) && std::isfinite(dy), "finite coordinates");
        double len = std::sqrt(dx * dx + dy * dy);
        // coordgen 内部坐标尺度：标准键长 50（上游 test_coordgen.cpp
        // expectedLength = 50.f 同锚），取宽区间防止过拟合。
        CHECK(len > 10.0 && len < 200.0, "bond length in plausible range");
        if (len < minLen) minLen = len;
        if (len > maxLen) maxLen = len;
    }
    CHECK(maxLen / minLen < 1.15, "six-ring template recognized (near-regular hexagon)");

    for (int i = 0; i < 6; ++i) {
        for (int j = i + 1; j < 6; ++j) {
            double dx = static_cast<double>(atoms[i]->getCoordinates().x())
                      - static_cast<double>(atoms[j]->getCoordinates().x());
            double dy = static_cast<double>(atoms[i]->getCoordinates().y())
                      - static_cast<double>(atoms[j]->getCoordinates().y());
            CHECK(std::sqrt(dx * dx + dy * dy) > 0.01, "atoms at distinct positions");
        }
    }

    for (int i = 0; i < 6; ++i) {
        const auto& c = atoms[i]->getCoordinates();
        std::printf("atom %d: (%.3f, %.3f)\n", i, c.x(), c.y());
    }

    if (failures != 0) {
        std::printf("coordgen test_package: %d/%d checks failed\n", failures, checks);
        return 1;
    }
    std::printf("coordgen test_package: %d/%d checks passed\n", checks, checks);
    return 0;
}
