#include <qqwing.hpp>

#include <cstdio>
#include <string>

static int failures = 0;

#define CHECK(cond, msg)                                                          \
    do {                                                                          \
        if (!(cond)) {                                                            \
            std::fprintf(stderr, "[FAIL] %s (%s:%d)\n", msg, __FILE__, __LINE__); \
            ++failures;                                                           \
        } else {                                                                  \
            std::printf("[ok] %s\n", msg);                                        \
        }                                                                         \
    } while (0)

// 验证 81 格解满足数独行列宫约束
static bool valid_solution(const int* sol) {
    if (sol == nullptr) return false;
    for (int r = 0; r < 9; ++r) {
        int seen[10] = {0};
        for (int c = 0; c < 9; ++c) {
            int v = sol[r * 9 + c];
            if (v < 1 || v > 9 || seen[v]) return false;
            seen[v] = 1;
        }
    }
    for (int c = 0; c < 9; ++c) {
        int seen[10] = {0};
        for (int r = 0; r < 9; ++r) {
            int v = sol[r * 9 + c];
            if (v < 1 || v > 9 || seen[v]) return false;
            seen[v] = 1;
        }
    }
    for (int br = 0; br < 3; ++br) {
        for (int bc = 0; bc < 3; ++bc) {
            int seen[10] = {0};
            for (int r = 0; r < 3; ++r) {
                for (int c = 0; c < 3; ++c) {
                    int v = sol[(br * 3 + r) * 9 + (bc * 3 + c)];
                    if (v < 1 || v > 9 || seen[v]) return false;
                    seen[v] = 1;
                }
            }
        }
    }
    return true;
}

int main() {
    // 1. 版本
    std::string ver = qqwing::getVersion();
    CHECK(ver == "1.3.4", "getVersion() == 1.3.4");
    if (ver != "1.3.4") std::fprintf(stderr, "       实得 %s\n", ver.c_str());

    // 2. 已知唯一解 puzzle（维基百科经典样例）
    int puzzle[81] = {
        5, 3, 0, 0, 7, 0, 0, 0, 0,
        6, 0, 0, 1, 9, 5, 0, 0, 0,
        0, 9, 8, 0, 0, 0, 0, 6, 0,
        8, 0, 0, 0, 6, 0, 0, 0, 3,
        4, 0, 0, 8, 0, 3, 0, 0, 1,
        7, 0, 0, 0, 2, 0, 0, 0, 6,
        0, 6, 0, 0, 0, 0, 2, 8, 0,
        0, 0, 0, 4, 1, 9, 0, 0, 5,
        0, 0, 0, 0, 8, 0, 0, 7, 9
    };
    int expected[81] = {
        5, 3, 4, 6, 7, 8, 9, 1, 2,
        6, 7, 2, 1, 9, 5, 3, 4, 8,
        1, 9, 8, 3, 4, 2, 5, 6, 7,
        8, 5, 9, 7, 6, 1, 4, 2, 3,
        4, 2, 6, 8, 5, 3, 7, 9, 1,
        7, 1, 3, 9, 2, 4, 8, 5, 6,
        9, 6, 1, 5, 3, 7, 2, 8, 4,
        2, 8, 7, 4, 1, 9, 6, 3, 5,
        3, 4, 5, 2, 8, 6, 1, 7, 9
    };

    qqwing::SudokuBoard board;
    CHECK(board.setPuzzle(puzzle), "setPuzzle() 接受已知 puzzle");
    CHECK(board.solve(), "solve() 返回 true");
    CHECK(board.isSolved(), "isSolved() 为 true");

    // 注意：hasUniqueSolution()/countSolutionsLimited() 内部会 reset() 清空 solution，
    // 必须在调用它们之前读取并验证解。
    const int* sol = board.getSolution();
    CHECK(sol != nullptr, "getSolution() 非空");
    bool match = true;
    for (int i = 0; i < 81; ++i) {
        if (sol[i] != expected[i]) { match = false; break; }
    }
    CHECK(match, "解与已知唯一解逐格一致");
    CHECK(valid_solution(sol), "解满足数独行列宫约束");

    CHECK(board.hasUniqueSolution(), "hasUniqueSolution() 为 true");
    CHECK(board.countSolutionsLimited() == 1, "countSolutionsLimited() == 1");

    // 3. generatePuzzle 生成 + 求解闭环
    qqwing::SudokuBoard gen;
    CHECK(gen.generatePuzzle(), "generatePuzzle() 返回 true");
    CHECK(gen.solve(), "生成的 puzzle 可解");
    const int* gp = gen.getPuzzle();
    const int* gs = gen.getSolution();
    CHECK(valid_solution(gs), "生成 puzzle 的解满足约束");
    bool consistent = true;
    for (int i = 0; i < 81; ++i) {
        if (gp[i] != 0 && gp[i] != gs[i]) { consistent = false; break; }
    }
    CHECK(consistent, "生成 puzzle 的解与给定数字一致");

    if (failures) {
        std::fprintf(stderr, "\nqqwing: %d 项断言失败\n", failures);
        return 1;
    }
    std::printf("\nqqwing 1.3.4: 全部断言通过\n");
    return 0;
}
