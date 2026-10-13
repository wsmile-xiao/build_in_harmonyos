// mINI 0.9.20 消费者用例（test_package）
// 目标：用**真实 INI 文本**走一遍交付头文件 mini/ini.h，把每个键/值/类型/往返结果
//       与手写期望值逐项比对；期望值来源 = 上游 README 的格式声明 + 上游
//       tests/testread.cpp 已有的用例期望（含 Malformed case 1/2、NotWellFormed）。
// 判据显式给出，不做"解析成功即通过"的自证式断言。
#include "mini/ini.h"

#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

static int g_checks = 0;
static int g_failed = 0;

static void compare(const std::string& what, const std::string& got,
                    const std::string& want)
{
    ++g_checks;
    if (got != want) {
        ++g_failed;
        std::cout << "FAIL " << what << ": got [" << got << "] want ["
                  << want << "]" << std::endl;
    } else {
        std::cout << "ok   " << what << " = [" << got << "]" << std::endl;
    }
}

static void compare_size(const std::string& what, std::size_t got,
                         std::size_t want)
{
    compare(what, std::to_string(got), std::to_string(want));
}

static void compare_bool(const std::string& what, bool got, bool want)
{
    compare(what, got ? "true" : "false", want ? "true" : "false");
}

static void compare_int(const std::string& what, int got, int want)
{
    compare(what, std::to_string(got), std::to_string(want));
}

static void compare_double(const std::string& what, double got, double want)
{
    ++g_checks;
    if (std::fabs(got - want) > 1e-12) {
        ++g_failed;
        std::ostringstream oss;
        oss << "FAIL " << what << ": got " << got << " want " << want;
        std::cout << oss.str() << std::endl;
    } else {
        std::cout << "ok   " << what << " = " << got << std::endl;
    }
}

static std::string read_bytes(const std::string& path)
{
    std::ifstream in(path, std::ios::in | std::ios::binary);
    std::ostringstream oss;
    oss << in.rdbuf();
    return oss.str();
}

static void write_bytes(const std::string& path, const std::string& bytes)
{
    std::ofstream out(path, std::ios::out | std::ios::binary | std::ios::trunc);
    out.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
}

// 真实 INI 文本样板：section / ; 注释 / # 行 / 行内注释 / 引号 / 空行 /
// CRLF 与 LF 混用 / 重复键 / UTF-8 值 / 数值 / 布尔字符串
static const char INI_SAMPLE[] =
    "\xEF\xBB\xBF"                                  // UTF-8 BOM（上游会剥离）
    "; 顶层注释：首字符为 ; 的行整行忽略\n"
    "# hash 行：mINI 不认 # 注释，但本行没有 '='，被当作 PDATA_UNKNOWN 忽略\n"
    "stray = orphan\n"                              // 首个 [section] 之前 -> 整行丢弃
    "\n"
    "[Server] ; 段行尾部的行内注释会被剥离\n"
    "Host = example.org   \n"                       // 值两侧空白被 trim
    "Port=8080\n"
    "port = 9090\r\n"                               // 重复键（仅大小写不同）+ CRLF 行
    "ratio = 0.125\n"
    "enabled = true\n"
    "enabled_upper = TRUE\n"                        // 值不做大小写折叠
    "quoted = \"hello world\"\n"                    // 引号不是语法，原样保留
    "trailing = value ; still part of value\n"      // 键值行的 ; 不剥离
    "eqvalue = a=b=c\n"                             // 值里允许 '='
    "esc\\=key = escaped-equals\n"                  // 键里的 '=' 必须写成 '\='
    "empty =\n"                                     // 空值
    "=emptykey\n"                                   // 空键名允许
    "\n"
    "[Ünïcode-段] ; UTF-8 段名\n"                    // 段名/值 UTF-8（上游 testutf8 同覆盖）
    "city = 東京\n"
    "emoji = 🚀\n"
    "note = 中文字符串\n"
    "enabled = false\r\n"                           // 段内再混一条 CRLF
    "[Client]\r\n"                                  // CRLF 段行
    "timeout = 30 ; seconds\n"
    "retries=3\n";

// 畸形 INI：数据与期望值逐字取自上游 tests/testread.cpp Malformed case 1（段名畸形）
static const char INI_MALFORMED_SECTIONS[] =
    "[[name1]\n"
    "key=value\n"
    "[name2]]\n"
    "key=value\n"
    "[[name3]]\n"
    "key=value\n";

// 畸形 INI：上游 tests/testread.cpp Malformed case 2（键名畸形，'\\=' 转义）
static const char INI_MALFORMED_KEYS[] =
    "[name]\n"
    "key\\==value\n"
    "\\===\n"
    "a\\= \\===b\n"
    "   c\\= \\=  =       =d \n";

int main()
{
    std::cout << "== 1) 真实 INI 文本解析（含 BOM / CRLF-LF 混用 / 注释 / 引号 / 重复键）"
              << std::endl;
    write_bytes("mini_sample.ini", std::string(INI_SAMPLE) + "");
    mINI::INIFile sample("mini_sample.ini");
    mINI::INIStructure ini;
    compare_bool("INIFile::read() 返回值", sample.read(ini), true);
    compare_size("段总数（server / Ünïcode-段 / client）", ini.size(), 3);

    // 首个 [section] 之前的键必须被丢弃（README: keys that do not belong to a section are ignored）
    bool orphan_found = false;
    for (auto const& sec : ini) {
        for (auto const& kv : sec.second) {
            if (kv.first == "stray") { orphan_found = true; }
        }
    }
    compare_bool("首个 [section] 之前的键 stray 被丢弃", orphan_found, false);

    compare_bool("ini.has(\"Server\") —— 段名大小写不敏感", ini.has("Server"), true);
    compare_bool("ini.has(\"SERVER\") —— 大写查询同样命中", ini.has("SERVER"), true);
    compare_bool("ini.has(\"no-such-section\")（不存在的段）",
                 ini.has("no-such-section"), false);

    // 段内键/值逐项比对
    compare("server.host（值两侧空白被 trim）", ini["server"]["host"], "example.org");
    compare("SERVER/HOST 大写查询（键名大小写不敏感）",
            ini["SERVER"]["HOST"], "example.org");
    compare("server.port（重复键 Port=8080 / port=9090 -> 后写胜出）",
            ini["server"]["port"], "9090");
    compare("server.ratio", ini["server"]["ratio"], "0.125");
    compare("server.enabled", ini["server"]["enabled"], "true");
    compare("server.enabled_upper（值 CASE 原样保留）",
            ini["server"]["enabled_upper"], "TRUE");
    compare("server.quoted（引号不是语法，原样保留）",
            ini["server"]["quoted"], "\"hello world\"");
    compare("server.trailing（键值行尾的 ; 属于值）",
            ini["server"]["trailing"], "value ; still part of value");
    compare("server.eqvalue（值里允许 '='）", ini["server"]["eqvalue"], "a=b=c");
    compare("server.\"esc=key\"（键里的 \\= 还原成 =）",
            ini["server"]["esc=key"], "escaped-equals");
    compare("server.empty（空值）", ini["server"]["empty"], "");
    compare("server.\"\"（空键名）", ini["server"][""], "emptykey");
    compare("server.get(\"nope\") 缺键返回空串", ini["server"].get("nope"), "");
    compare_bool("server.has(\"nope\") = false", ini["server"].has("nope"), false);
    compare_bool("server.has(\"HOST\")（键名大小写不敏感）",
                 ini["server"].has("HOST"), true);

    // 键顺序 = 首次出现顺序，重复键就地更新（README: order is preserved）
    std::vector<std::string> keys;
    for (auto const& kv : ini["server"]) { keys.push_back(kv.first); }
    std::vector<std::string> want_keys = {"host", "port", "ratio", "enabled",
                                          "enabled_upper", "quoted", "trailing",
                                          "eqvalue", "esc=key", "empty", ""};
    compare_size("server 键数量（重复键不新增条目）", keys.size(), want_keys.size());
    compare_bool("server 键顺序 = 首次出现顺序",
                 keys == want_keys, true);

    // UTF-8 段名 / UTF-8 值
    compare_bool("ini.has(\"Ünïcode-段\") —— UTF-8 段名", ini.has("Ünïcode-段"), true);
    compare("Ünïcode-段.city", ini["Ünïcode-段"]["city"], "東京");
    compare("Ünïcode-段.emoji", ini["Ünïcode-段"]["emoji"], "🚀");
    compare("Ünïcode-段.note", ini["Ünïcode-段"]["note"], "中文字符串");
    compare("Ünïcode-段.enabled（CRLF 行同样读对）",
            ini["Ünïcode-段"]["enabled"], "false");
    compare("client.timeout（行内 ; 不属于值）",
            ini["client"]["timeout"], "30 ; seconds");
    compare("client.retries", ini["client"]["retries"], "3");

    std::cout << "== 2) 消费者侧类型转换（数值 / 布尔字符串）" << std::endl;
    compare_int("std::stoi(client.retries)", std::stoi(ini["client"]["retries"]), 3);
    compare_int("std::stoi(server.port)", std::stoi(ini["server"]["port"]), 9090);
    compare_double("std::stod(server.ratio)", std::stod(ini["server"]["ratio"]), 0.125);
    compare_double("std::stof(server.ratio) 保留位",
                   static_cast<double>(std::stof(ini["server"]["ratio"])), 0.125);
    compare_int("std::stoi(client.timeout) 只取行内注释前的数值前缀",
                std::stoi(ini["client"]["timeout"]), 30);
    compare_bool("server.enabled == \"true\"",
                 ini["server"]["enabled"] == "true", true);
    compare_bool("server.enabled_upper == \"true\"（值不折叠 -> 消费者需自行归一化）",
                 ini["server"]["enabled_upper"] == "true", false);
    // 消费者归一化后两者应当一致（这是 mINI 的既定语义：值原样交付）
    std::string norm_upper = ini["server"]["enabled_upper"];
    for (auto& c : norm_upper) { c = static_cast<char>(std::tolower(static_cast<unsigned char>(c))); }
    compare_bool("归一化后 enabled_upper 与 enabled 语义一致",
                 norm_upper == ini["server"]["enabled"], true);

    std::cout << "== 3) 边界/错误路径：畸形 INI 行为与上游 testread 期望一致" << std::endl;
    write_bytes("mini_malformed_sections.ini", INI_MALFORMED_SECTIONS);
    mINI::INIFile malformed("mini_malformed_sections.ini");
    mINI::INIStructure bad;
    compare_bool("畸形段名文件 read() 仍返回 true", malformed.read(bad), true);
    compare_size("畸形段名 -> 3 个段", bad.size(), 3);
    compare("畸形段名 \"[[name1]\" -> 段名 \"[name1\"",
            bad.get("[name1").get("key"), "value");
    compare("畸形段名 \"[name2]]\" -> 段名 \"name2]\"",
            bad.get("name2]").get("key"), "value");
    compare("畸形段名 \"[[name3]]\" -> 段名 \"[name3]\"",
            bad.get("[name3]").get("key"), "value");
    write_bytes("mini_malformed_keys.ini", INI_MALFORMED_KEYS);
    mINI::INIFile badmin("mini_malformed_keys.ini");
    mINI::INIStructure badk;
    compare_bool("畸形键名文件 read() 仍返回 true", badmin.read(badk), true);
    compare_size("畸形键名 -> 1 个段 name", badk.size(), 1);
    compare("畸形键 \"key\\==value\" -> 键 \"key=\"",
            badk.get("name").get("key="), "value");
    compare("畸形键 \"\\===\" -> 键 \"=\"", badk.get("name").get("="), "=");
    compare("畸形键 \"a\\= \\===b\" -> 键 \"a= =\"",
            badk.get("name").get("a= ="), "=b");
    compare("畸形键 \"   c\\= \\=  = =d \" -> 键 \"c= =\"",
            badk.get("name").get("c= ="), "=d");

    // 无 '=' 的垃圾行整行忽略（上游 NotWellFormed 数据同款行为）
    write_bytes("mini_garbage.ini",
                "GARBAGE\n"
                "    ; abcd   \n"
                "[first section]   ;test comment\n"
                "someKey= 1\n"
                "GARBAGE\n"
                "anotherKey =2\n");
    mINI::INIFile garbage("mini_garbage.ini");
    mINI::INIStructure gini;
    compare_bool("含 GARBAGE 行 + 段行注释的文件 read() = true",
                 garbage.read(gini), true);
    compare_size("GARBAGE 行不产生段", gini.size(), 1);
    compare("段行尾部注释被剥离 -> 段名 first section",
            gini.get("first section").get("somekey"), "1");
    compare("GARBAGE 行不产生键", gini.get("first section").get("anotherkey"), "2");
    compare_size("段内键数 = 2（GARBAGE 未混入）",
                 gini.get("first section").size(), 2);

    // 不存在的文件 -> read() 返回 false（不抛异常）
    mINI::INIFile missing("mini_definitely_missing_file.ini");
    mINI::INIStructure miss;
    compare_bool("读取不存在的文件 -> read() = false", missing.read(miss), false);

    // 空文件 -> read() = true 且 0 个段
    write_bytes("mini_empty.ini", "");
    mINI::INIFile emptyf("mini_empty.ini");
    mINI::INIStructure eini;
    compare_bool("空文件 read() = true", emptyf.read(eini), true);
    compare_size("空文件 0 个段", eini.size(), 0);

    std::cout << "== 4) generate() 输出逐字节比对" << std::endl;
    mINI::INIStructure gen;
    gen["alpha"]["k1"] = "v1";
    gen["alpha"]["k2"] = "  v2  ";     // generate() 会 trim 值
    gen["beta"]["a=b"] = "x";          // 键里的 '=' 写出时转义成 '\='
    mINI::INIFile genfile("mini_generated.ini");
    compare_bool("generate() 返回 true", genfile.generate(gen), true);
    compare("generate() 逐字节输出（紧凑格式）",
            read_bytes("mini_generated.ini"),
            "[alpha]\nk1=v1\nk2=v2\n[beta]\na\\=b=x");
    compare_bool("generate(pretty=true) 返回 true",
                 genfile.generate(gen, true), true);
    compare("generate(pretty=true) 逐字节输出",
            read_bytes("mini_generated.ini"),
            "[alpha]\nk1 = v1\nk2 = v2\n\n[beta]\na\\=b = x");

    std::cout << "== 5) write() 惰性写：保留注释与未改动行" << std::endl;
    write_bytes("mini_lazy.ini",
                "; keep this comment\n[sec]\nkey1=old\nkey2=keep\n");
    mINI::INIFile lazy("mini_lazy.ini");
    mINI::INIStructure lini;
    compare_bool("惰性写前 read() = true", lazy.read(lini), true);
    lini["sec"]["key1"] = "new";
    lini["sec"]["key3"] = "added";
    compare_bool("write() 返回 true", lazy.write(lini), true);
    compare("write() 后逐字节输出（注释保留 + 就地更新 + 追加新键）",
            read_bytes("mini_lazy.ini"),
            "; keep this comment\n[sec]\nkey1=new\nkey2=keep\nkey3=added\n");

    std::cout << "----------------------------------------" << std::endl;
    std::cout << "checks=" << g_checks << " failed=" << g_failed << std::endl;
    if (g_failed != 0) { return 1; }
    std::cout << "ALL CONSUMER CHECKS PASSED" << std::endl;
    return 0;
}
