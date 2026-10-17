// test_bpp_phyl_omics.cpp — libbpp-phyl-omics 2.4.1 消费者测试（真实调用被测包 API）
//
// 覆盖：CountClustersMafStatistics（上游提供、公开导出）的构造、getTreeProperty /
// setTreeProperty / getPropertyName / getShortName / getFullName —— 全部为纯内存
// 操作，无 IO / 显示器依赖，真实引用被测包与 bpp-phyl / bpp-seq-omics 的公开头文件，
// 并在最终链接时把 libbpp-phyl-omics.a 连同其依赖静态归档一起链入。
#include <Bpp/Seq/Io/Maf/CountClustersMafStatistics.h>

#include <iostream>
#include <string>

using namespace bpp;

static int passed = 0;
static void check(bool cond, const char* what)
{
    if (cond) { passed++; std::cout << "CHECK OK " << passed << "/5  " << what << "\n"; }
    else { std::cerr << "CHECK FAIL " << what << "\n"; }
}

int main()
{
    CountClustersMafStatistics stats("tree", 0.5);   // 构造（公开）
    check(stats.getTreeProperty() == "tree", "getTreeProperty after ctor");
    check(stats.getPropertyName() == "CountClusters", "getPropertyName");
    check(stats.getShortName() == "CountClusters(0.5)", "getShortName");
    check(stats.getFullName().find("divergence") != std::string::npos,
          "getFullName mentions divergence");
    stats.setTreeProperty("newTree");                // 修改属性
    check(stats.getTreeProperty() == "newTree", "setTreeProperty + getTreeProperty");

    std::cout << "passed " << passed << "/5" << std::endl;
    return passed == 5 ? 0 : 1;
}
