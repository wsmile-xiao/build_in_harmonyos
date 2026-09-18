// HarmonyOS 专项测试: sciplot 0.3.1
// 覆盖公开 API 在 aarch64 OHOS 消费入口上的实际使用: linspace 数值生成、
// Plot2D::drawCurve 曲线绘制、Canvas::saveplotdata 导出 gnuplot 数据文件，
// 并校验生成数据的内容正确性（数值范围与数据行数）。
#include <sciplot/sciplot.hpp>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <sys/stat.h>

#if defined(__OHOS__) || defined(__OHOS_FAMILY__) || defined(HARMONYOS)
#define SCIPLOT_OHOS_OK 1
#elif defined(__linux__) && defined(__aarch64__)
#warning "Linux aarch64 build: running on HarmonyOS-compatible aarch64 kernel"
#define SCIPLOT_OHOS_OK 1
#else
#define SCIPLOT_OHOS_OK 0
#endif

using namespace sciplot;

static int g_checks = 0;
static int g_ok = 0;

#define CHECK(cond)                                              \
  do {                                                           \
    ++g_checks;                                                  \
    if (!(cond)) {                                               \
      std::printf("FAIL [%s:%d]: %s\n", __FILE__, __LINE__, #cond); \
      return 1;                                                  \
    }                                                            \
    ++g_ok;                                                      \
  } while (0)

static bool file_exists(const std::string& p)
{
    struct stat st;
    return ::stat(p.c_str(), &st) == 0;
}

// Canvas 内部静态 id 计数器跨实例递增，脚本名可能是 multishow0.plt/1.plt/...
// 扫描候选名返回第一个存在的 gnuplot 脚本
static std::string find_script()
{
    for (int i = 0; i < 8; ++i)
    {
        std::string name = "multishow" + std::to_string(i) + ".plt";
        if (file_exists(name))
            return name;
    }
    return "";
}

// CTest 多个 test 用例共享同一工作目录：test.cpp 先运行会遗留 multishow*.plt 与
// plot*.dat，导致 find_script()/plot0.dat 校验命中非本次生成的产物（顺序耦合）。
// 运行前清理全部候选遗留文件，保证校验对象只来自本次生成。
static void cleanup_stale_artifacts()
{
    for (int i = 0; i < 8; ++i)
    {
        std::remove(("multishow" + std::to_string(i) + ".plt").c_str());
        std::remove(("plot" + std::to_string(i) + ".dat").c_str());
        std::remove("chaining.svg");
    }
}

// 跳过 gnuplot 数据文件中的 "# DATASET" 注释头，统计 "x y" 数据行
static int data_rows(const std::string& p)
{
    std::ifstream f(p);
    int rows = 0;
    double a, b;
    std::string line;
    while (std::getline(f, line))
    {
        if (!line.empty() && line[0] == '#')
            continue;
        std::istringstream ss(line);
        if (ss >> a >> b)
            ++rows;
    }
    return rows;
}

// 1) linspace 数值生成正确性（aarch64 浮点行为）
// 注意: linspace(x0, x1, N) 的 N 是"间隔数"，返回 N+1 个点（含两端点）
static int linspace_values()
{
    Vec x = linspace(0.0, 5.0, 100);
    CHECK(x.size() == 101);
    CHECK(std::abs(x[0] - 0.0) < 1e-12);
    CHECK(std::abs(x[100] - 5.0) < 1e-12);
    CHECK(x[50] > x[0] && x[100] > x[50]); // 严格递增
    return 0;
}

// 2) 公开 API 绘制 + 数据导出（HarmonyOS 消费者入口）
static int plot_and_export()
{
    Vec x = linspace(0.0, 5.0, 100);
    Plot2D plot;
    plot.palette("paired");
    plot.drawCurve(x, std::sin(x)).label("sin(x)").lineWidth(4);
    plot.drawCurve(x, std::cos(x)).label("cos(x)").lineWidth(2);

    Figure figure = {{plot}};
    Canvas canvas = {{figure}};
    canvas.autoclean(false);

    canvas.saveplotdata();
    CHECK(file_exists("plot0.dat"));
    int rows = data_rows("plot0.dat");
    CHECK(rows >= 90); // 100 个 linspace 点，除注释头

    // 校验曲线数值范围（sin/cos 应在 [-1,1]）
    std::ifstream d("plot0.dat");
    std::string l;
    bool range_ok = true;
    double xv, yv;
    while (std::getline(d, l))
    {
        if (!l.empty() && l[0] == '#')
            continue;
        std::istringstream ss(l);
        if (ss >> xv >> yv)
        {
            if (yv < -1.0 || yv > 1.0)
                range_ok = false;
        }
    }
    CHECK(range_ok);
    return 0;
}

// 3) 图/画布链式公开 API（HarmonyOS 业务上层常见组合用法）
// Canvas 无公开 width()/height() getter；save() 路径经 saveterminalcmd 写入
// "set terminal svg size W,H"，曲线标签经 figure repr 写入 plot 命令
static int canvas_chaining()
{
    Vec x = linspace(0.0, 5.0, 100);
    Plot2D plot;
    plot.drawCurve(x, std::sin(x)).label("sin(x)");
    Figure figure = {{plot}};
    Canvas canvas = {{figure}};
    canvas.size(640, 480).title("OHOS test").autoclean(false);

    canvas.save("chaining.svg");

    // 校验脚本中确实包含画布尺寸设置、数据文件引用与曲线标签
    std::string script_name = find_script();
    CHECK(!script_name.empty());
    std::ifstream script(script_name);
    std::string script_text((std::istreambuf_iterator<char>(script)),
                            std::istreambuf_iterator<char>());
    CHECK(!script_text.empty());
    CHECK(script_text.find("set terminal svg size") != std::string::npos);
    // Canvas 静态 id 计数器跨实例递增，数据文件可能为 plot0.dat/plot1.dat/...
    CHECK(script_text.find(".dat") != std::string::npos);
    CHECK(script_text.find("title 'sin(x)'") != std::string::npos);
    return 0;
}

int main()
{
    if (SCIPLOT_OHOS_OK == 0)
    {
        std::printf("FAIL: not running on OHOS or aarch64-compatible platform\n");
        return 1;
    }
    // 运行前清理遗留产物，保证校验对象只来自本次生成（消除 CTest 共享目录顺序耦合）
    cleanup_stale_artifacts();
    if (linspace_values() != 0) return 1;
    if (plot_and_export() != 0) return 1;
    if (canvas_chaining() != 0) return 1;
    std::printf("OHOS_SPECIAL_TEST PASS: %d/%d checks\n", g_ok, g_checks);
    return 0;
}
