// test_bpp_seq_omics.cpp — libbpp-seq-omics 2.4.1 消费者测试（真实调用被测包 API）
//
// 覆盖：MafStatisticsResult 的默认构造、setValue 写入、hasValue 查询、
// getAvailableTags 列表 —— 全部为纯内存操作，无 IO/显示器依赖。
#include <Bpp/Seq/Io/Maf/MafStatistics.h>
#include <iostream>

using namespace bpp;

static int passed = 0;
static void check(bool cond, const char* what)
{
    if (cond) { passed++; std::cout << "CHECK OK " << passed << "/3  " << what << "\n"; }
    else { std::cerr << "CHECK FAIL " << what << "\n"; }
}

int main()
{
    MafStatisticsResult r;                       // 默认构造（公开）
    check(r.getAvailableTags().empty(), "empty result has no tags");
    r.setValue("foo", 3.14);                     // double 重载，真实写入
    check(r.hasValue("foo"), "hasValue after setValue");
    check(r.getAvailableTags().size() == 1, "one tag available after setValue");

    std::cout << "passed " << passed << "/3" << std::endl;
    return passed == 3 ? 0 : 1;
}
