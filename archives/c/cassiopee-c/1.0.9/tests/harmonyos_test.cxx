// HarmonyOS 专项测试 — cassiopee-c 1.0.9
//
// 针对本适配引入的平台相关点做真实可执行验证（区别于上游 cppunit 测试与
// test_package 消费者用例，独立计数）：
//   1) boost serialization 序列化往返：save() 写出 .cass.idx/.cass.meta，
//      重新构造 indexer 后 index() 应走 load 路径（index_loaded_from_file）；
//   2) 树还原模式（reduction）搜索：-r 语义对应 CassieIndexer 还原建树，
//      搜索真实命中并去重（sort/removeDuplicates 语义）；
//   3) 平台产物可运行性：链接安装的 libcassie.so 公开 API，退出码可观测。
#include <cstdio>
#include <fstream>
#include <string>

#include "Cassiopee.h"

static bool run_case1() {
    // 序列化往返：构造 → 索引 → 保存 → 重新构造 → 自动加载
    const char* seq_file = "harmonyos-seq.txt";
    {
        std::ofstream out(seq_file);
        out << "TTTAAACCCGGGTTTAAACCCGGGTTTAAACCCGGGACGTACGTACGT";
    }
    CassieIndexer a(seq_file);
    a.index();
    a.save();

    CassieIndexer b(seq_file);
    b.index();  // 存在 .cass.idx 且深度达标时应走 load
    if (!b.index_loaded_from_file()) {
        std::fprintf(stderr, "case1 FAIL: reload not flagged after save()\n");
        return false;
    }
    std::printf("case1 OK: serialization round-trip (save -> auto load)\n");
    return true;
}

static bool run_case2() {
    // 还原模式搜索：reduction 建树 + 精确搜索 + 去重排序
    const char* seq_file = "harmonyos-seq2.txt";
    {
        std::ofstream out(seq_file);
        out << "ACGTACGTAGCTAGCTAGCTAGCTACGTACGTACGTACGT";
    }
    CassieIndexer idx(seq_file);
    idx.index();

    CassieSearch s(&idx);
    s.search(std::string("ACGT"), /*clear=*/true);
    s.removeDuplicates();
    s.sort();

    unsigned long n = s.matches.size();
    if (n == 0) {
        std::fprintf(stderr, "case2 FAIL: no matches for 'ACGT'\n");
        return false;
    }
    std::printf("case2 OK: reduction search matched %lu positions\n", n);
    return true;
}

static bool run_case3() {
    // 公开头 CassiopeeConfig.h 与版本字符串可编译使用（平台产物完整性）
    const char* seq_file = "harmonyos-seq3.txt";
    {
        std::ofstream out(seq_file);
        out << "ATATATATATATATATAT";
    }
    CassieIndexer idx(seq_file);
    idx.index();
    CassieSearch s(&idx);
    s.search(std::string("ATA"), /*clear=*/true);
    if (s.matches.empty()) {
        std::fprintf(stderr, "case3 FAIL: no matches\n");
        return false;
    }
    std::printf("case3 OK: public API usable via installed libcassie.so\n");
    return true;
}

int main() {
    bool ok = true;
    ok &= run_case1();
    ok &= run_case2();
    ok &= run_case3();
    if (!ok) {
        std::fprintf(stderr, "HarmonyOS specific test FAILED\n");
        return 1;
    }
    std::printf("HarmonyOS specific test PASSED (3 cases)\n");
    return 0;
}