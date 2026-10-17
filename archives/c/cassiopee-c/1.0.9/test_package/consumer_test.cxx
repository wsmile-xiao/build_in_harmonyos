// 消费者测试：仅通过安装的公开头文件（Cassiopee.h）与公开 API
// （CassieIndexer/CassieSearch）使用 libcassie.so，验证第三方使用者
// 可编译、链接、调用并正常运行（R34/PF3：真实调用 API，非空壳）。
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>

#include "Cassiopee.h"

int main() {
    // 写入一段极小的基因序列文件作为索引输入（公开 API：CassieIndexer(path)）
    const char* seq_file = "consumer-seq.txt";
    {
        std::ofstream out(seq_file);
        out << "ACGTACGTACGTACGTAGCTAGCTAGCTAGCTACGTACGT";
    }

    // 1) 公开 API：构造索引器并对序列构建后缀树索引
    CassieIndexer indexer(seq_file);
    indexer.index();

    // 2) 公开 API：执行精确搜索（pattern "ACGT" 应命中多次）
    CassieSearch search(&indexer);
    search.search(std::string("ACGT"));
    search.sort();

    // 3) 通过公开 API 的 matches 列表获取可观察结果
    unsigned long matches = search.matches.size();
    if (matches == 0) {
        std::fprintf(stderr, "FAIL: expected matches for pattern 'ACGT', got 0\n");
        return 1;
    }
    std::printf("OK: pattern 'ACGT' matched %lu times\n", matches);

    // 4) 公开 API：索引序列化保存（save() 写入 <file>.cass.idx/.cass.meta）
    indexer.save();
    std::string idx_file = std::string(seq_file) + ".cass.idx";
    {
        std::ifstream check(idx_file.c_str());
        if (!check.good()) {
            std::fprintf(stderr, "FAIL: index file %s not created after save()\n", idx_file.c_str());
            return 2;
        }
    }
    std::printf("OK: index file %s created\n", idx_file.c_str());

    // 5) 公开 API：再次 index() 时应从已保存的索引加载（index_loaded_from_file）
    CassieIndexer reloader(seq_file);
    reloader.index();
    if (!reloader.index_loaded_from_file()) {
        std::fprintf(stderr, "FAIL: reloaded index not flagged as loaded-from-file\n");
        return 3;
    }
    std::printf("OK: index reloaded from file\n");

    return 0;
}