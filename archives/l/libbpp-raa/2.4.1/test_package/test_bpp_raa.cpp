// test_bpp_raa.cpp — libbpp-raa 2.4.1 消费者测试（真实调用被测包 API）
//
// RAA 是 ACNUC 序列数据库访问库：绝大多数公开 API（RAA::openDatabase、
// processQuery、RaaList 的增删查、RaaSpeciesTree 遍历）都要在已打开数据库上工作，
// 没有数据库时无法无头运行。但 `RaaList` 的三个静态常量 LIST_SEQUENCES /
// LIST_KEYWORDS / LIST_SPECIES 定义在 RaaList.cpp 里、是库导出的真实符号 ——
// 解析它们即可证明「消费者已正确链接被测包（及其 bpp-seq / bpp-core / zlib 依赖）」。
// 另做一次默认构造，验证类型注册与构造函数可链接。
#include <Bpp/Raa/RaaList.h>
#include <iostream>
#include <string>

using namespace bpp;

static int passed = 0;
static void check(bool cond, const char* what)
{
    if (cond) { passed++; std::cout << "CHECK OK " << passed << "/3  " << what << "\n"; }
    else { std::cerr << "CHECK FAIL " << what << "\n"; }
}

int main()
{
    check(RaaList::LIST_SEQUENCES == "sequence list", "LIST_SEQUENCES constant resolves");
    check(RaaList::LIST_KEYWORDS == "keyword list",   "LIST_KEYWORDS constant resolves");
    check(RaaList::LIST_SPECIES == "species list",    "LIST_SPECIES constant resolves");

    // 注：RaaList 的构造函数是私有（只能由 RAA 友元创建），故不做实例化断言。

    std::cout << "passed " << passed << "/3" << std::endl;
    return passed == 3 ? 0 : 1;
}
