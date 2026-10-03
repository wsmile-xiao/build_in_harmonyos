#include <cstdlib>
#include <iostream>
#include <string>

#include <nanodbc/nanodbc.h>

namespace {

int failures = 0;

void check(bool ok, const char* what)
{
    std::cout << (ok ? "[ok]   " : "[FAIL] ") << what << std::endl;
    if (!ok)
        ++failures;
}

} // namespace

int main()
{
    // ===== 离线冒烟：不依赖任何数据库服务（OHOS PC 沙箱无 ODBC 数据源）=====
    // 依据上游语义：未连接状态下 connected()==false、disconnect() 无害、
    // statement 默认构造未打开、result 默认构造 impl_==nullptr → operator bool
    // 为 false、transactions()==0（纯成员读取）。所有调用均为无网络/无驱动行为。

    // A1 connection 默认构造：不触碰驱动管理器（connection_impl 仅清零成员）
    nanodbc::connection conn;
    check(!conn.connected(), "connection 默认构造后 connected()==false");

    // A2 connected() 幂等
    check(!conn.connected(), "connected() 幂等（仍为 false）");

    // A3 未连接事务数 == 0（纯成员读取）
    check(conn.transactions() == 0, "未连接 transactions()==0");

    // A4 未连接 disconnect() 为无害 no-op（dbc_==nullptr 分支直接返回）
    conn.disconnect();
    check(!conn.connected(), "未连接 disconnect() 后仍为 false（no-op）");

    // A5 statement 默认构造：open_/stmt_ 清零，不触碰连接
    nanodbc::statement stmt;
    check(!stmt.connected(), "statement 默认构造后 connected()==false");

    // A6 statement 空状态下 close() 无害（上游 API）
    stmt.close();
    check(!stmt.connected(), "statement close() 后仍为 false（no-op）");

    // A7 result 默认构造（public 构造，impl_==nullptr）→ operator bool == false
    nanodbc::result r;
    check(!static_cast<bool>(r), "result 默认构造 operator bool==false");

    // A8 date/time/timestamp 哨兵类型可离线构造（纯 POD，无驱动交互）
    nanodbc::date d{2026, 1, 2};
    nanodbc::time t{12, 34, 56};
    nanodbc::timestamp ts{2026, 1, 2, 3, 4, 5, 6};
    check(d.year == 2026 && t.hour == 12 && ts.fract == 6,
          "date/time/timestamp POD 构造正常");

    // A9 database_error 可离线构造（不触碰句柄，仅存 info）
    try
    {
        throw nanodbc::database_error(nullptr, 0, "offline sentinel");
    }
    catch (const nanodbc::database_error& e)
    {
        check(std::string(e.what()).find("offline sentinel") != std::string::npos,
              "database_error 离线构造 what() 正常");
    }

    // ===== 消费者形态：链接交付的 libnanodbc.a + 交付头 include/nanodbc/nanodbc.h =====
    // 上面的每一处调用都已真实经过交付库符号（connected/transactions/disconnect/
    // reset/operator bool 均在 libnanodbc 的 nanodbc.cpp 编译单元中实现）。
    // CI 的 L1e 移走 lib/include 后重跑 conan test，find_package(nanodbc) 或
    // 链接步骤必然失败——本测试真依赖被测包。

    std::cout << (failures == 0 ? "ALL OFFLINE CHECKS PASSED"
                                : "FAILURES DETECTED")
              << std::endl;
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
