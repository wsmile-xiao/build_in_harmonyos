// SOCI 4.0.3 完整消费者用例（平台 rule12）—— 不是断言集合，而是把 SOCI 当成
// 真实消费者来用一遍：SQLite3 后端 + 内存库 + 预编译语句 + 参数绑定 +
// rowset/row 迭代 + 列元数据 + NULL 指示器 + 事务提交/回滚 + 错误处理。
// 每一步都产出可核对的结果（行数、求和、平均值、绑定值、错误消息）。
#include <soci/soci.h>
#include <soci/sqlite3/soci-sqlite3.h>

#include <cmath>
#include <iostream>
#include <sstream>
#include <string>

namespace {

int g_checks = 0;
int g_failed = 0;

void check(bool ok, std::string const &what, std::string const &detail = std::string())
{
    ++g_checks;
    if (!ok) {
        ++g_failed;
    }
    std::cout << "  [" << (ok ? "ok" : "FAIL") << "] " << what;
    if (!detail.empty()) {
        std::cout << "  " << detail;
    }
    std::cout << std::endl;
}

std::string fmt(double value)
{
    std::ostringstream os;
    os << value;
    return os.str();
}

} // namespace

int main()
{
    std::cout << "SOCI 消费者用例：SQLite3 后端 + 真实数据访问全流程" << std::endl;

    // ① 后端工厂：SOCI 的后端是独立库（soci_sqlite3），这一句同时证明它被真正链接。
    soci::backend_factory const &backEnd = *soci::factory_sqlite3();
    check(true, "加载 sqlite3 后端工厂 factory_sqlite3()");

    // ② 打开内存数据库
    soci::session sql(backEnd, ":memory:");
    check(sql.is_connected(), "打开 SQLite3 内存数据库",
          "backend=" + sql.get_backend_name());

    // ③ DDL
    sql << "create table measurement ("
           "  id integer primary key, name text, value real, note text)";
    check(true, "建表 measurement(id, name, value, note)");

    // ④ 预编译语句 + use() 参数绑定，连续写入 1000 行（每 100 行写一个 NULL note）
    const int rows = 1000;
    {
        int id = 0;
        std::string name;
        double value = 0.0;
        std::string note;
        soci::indicator note_ind = soci::i_ok;
        soci::statement ins = (sql.prepare <<
            "insert into measurement(id, name, value, note) values(:id, :name, :value, :note)",
            soci::use(id), soci::use(name), soci::use(value), soci::use(note, note_ind));
        for (int i = 1; i <= rows; ++i) {
            id = i;
            name = "sensor-" + std::to_string(i % 10);
            value = i * 0.5;
            if (i % 100 == 0) {
                note_ind = soci::i_null;      // 第 100/200/... 行写 NULL
            } else {
                note = "row-" + std::to_string(i);
                note_ind = soci::i_ok;
            }
            ins.execute(true);
        }
    }
    int n_inserted = 0;
    sql << "select count(*) from measurement", soci::into(n_inserted);
    check(n_inserted == rows, "预编译语句写入 1000 行", "count=" + std::to_string(n_inserted));

    // ⑤ 聚合查询：count / sum / avg
    int count = 0;
    double sum = 0.0, avg = 0.0;
    sql << "select count(*), sum(value), avg(value) from measurement",
        soci::into(count), soci::into(sum), soci::into(avg);
    check(count == 1000 && std::fabs(sum - 250250.0) < 1e-6 && std::fabs(avg - 250.25) < 1e-9,
          "聚合 count/sum/avg = 1000 / 250250.0 / 250.25",
          "sum=" + fmt(sum) + " avg=" + fmt(avg));

    // ⑥ rowset<soci::row> 迭代 + 列元数据（列名 / 类型）
    int iterated = 0;
    std::string col0_name, col0_datatype;
    {
        soci::rowset<soci::row> rs =
            (sql.prepare << "select id, name, value, note from measurement "
                            "where id <= 10 order by id");
        for (soci::rowset<soci::row>::const_iterator it = rs.begin(); it != rs.end(); ++it) {
            soci::row const &r = *it;
            if (iterated == 0) {
                col0_name = r.get_properties(0).get_name();
                col0_datatype = std::to_string(
                    static_cast<int>(r.get_properties(0).get_data_type()));
            }
            ++iterated;
        }
    }
    check(iterated == 10, "rowset 迭代 10 行", "iterated=" + std::to_string(iterated));
    check(col0_name == "id", "列元数据：第 0 列名 == id（data_type=" + col0_datatype + "）");

    // ⑦ NULL 指示器：读回第 100 行的 note
    {
        soci::indicator ind = soci::i_ok;
        std::string note = "sentinel";
        sql << "select note from measurement where id = 100", soci::into(note, ind);
        check(ind == soci::i_null, "NULL 指示器：第 100 行 note 读回 i_null");
    }

    // ⑧ 事务回滚：写入后回滚，行数必须不变（真实业务语义）
    {
        int before = 0;
        sql << "select count(*) from measurement", soci::into(before);
        {
            soci::transaction tr(sql);
            sql << "insert into measurement(name, value) values('rolled-back', 1.0)";
            tr.rollback();
        }
        int after = 0;
        sql << "select count(*) from measurement", soci::into(after);
        check(before == after && after == rows, "事务回滚后行数不变",
              std::to_string(before) + " -> " + std::to_string(after));
    }

    // ⑨ 事务提交：行数 +1
    {
        {
            soci::transaction tr(sql);
            sql << "insert into measurement(name, value) values('committed', 2.0)";
            tr.commit();
        }
        int after = 0;
        sql << "select count(*) from measurement", soci::into(after);
        check(after == rows + 1, "事务提交后行数 = 1001", "count=" + std::to_string(after));
    }

    // ⑩ 参数化查询（use + into）：id=500 -> value=250.0
    {
        int target = 500;
        double value = 0.0;
        sql << "select value from measurement where id = :id",
            soci::use(target), soci::into(value);
        check(std::fabs(value - 250.0) < 1e-9, "参数化查询 id=500 -> value=250.0",
              "value=" + fmt(value));
    }

    // ⑪ 错误处理：非法 SQL 抛 soci_error 且带后端消息
    {
        bool threw = false;
        std::string message;
        try {
            sql << "select * from no_such_table";
        } catch (soci::soci_error const &e) {
            threw = true;
            message = e.what();
        }
        check(threw && !message.empty(), "非法 SQL 抛 soci_error 并带错误消息",
              message.substr(0, 60));
    }

    // ⑫ 后端真正链接的证据 ①：通过 SOCI 的 sqlite_api 命名空间取 SQLite 版本
    {
        char const *v = sqlite_api::sqlite3_libversion();
        std::string version = v ? v : "";
        check(!version.empty() && version.substr(0, 2) == "3.",
              "sqlite_api::sqlite3_libversion() = " + version + "（sqlite3 依赖真正链接进来）");
    }

    // ⑬ 后端真正链接的证据 ②：查询 SQLite 系统表 sqlite_master（库内部结构可读）
    {
        int tables = 0;
        sql << "select count(*) from sqlite_master where type = 'table'",
            soci::into(tables);
        check(tables == 1, "sqlite_master 中 1 张用户表", "tables=" + std::to_string(tables));
    }

    std::cout << "SOCI 消费者用例完成：" << (g_checks - g_failed) << "/" << g_checks
              << " 步通过" << std::endl;
    if (g_failed != 0) {
        std::cout << "FAILED checks: " << g_failed << std::endl;
        return 1;
    }
    std::cout << "Verdict: PASS" << std::endl;
    return 0;
}
