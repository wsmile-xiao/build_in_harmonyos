// test_package consumer test — sciplot 0.3.1 (header-only, C++17)
// 消费者视角: 仅通过已安装/导出的公开头文件 <sciplot/sciplot.hpp> 与公开 API
// (Plot2D::drawCurve / Figure / Canvas::save / Canvas::saveplotdata) 构建、链接并运行，
// 验证生成的可观察产物（gnuplot 数据文件与脚本）真实存在且内容正确。
#include <sciplot/sciplot.hpp>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <sys/stat.h>

using namespace sciplot;

static bool exists(const std::string& p)
{
    struct stat st;
    return ::stat(p.c_str(), &st) == 0;
}

// 跳过 "#..." 注释头（gnuplot 数据文件带 DATASET 注释），统计 "x y" 数据行
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

int main()
{
    // 公开 API: 生成 x 轴数据并绘制两条曲线
    Vec x = linspace(0.0, 5.0, 100);
    Plot2D plot;
    plot.palette("paired");
    plot.drawCurve(x, std::sin(x)).label("sin(x)").lineWidth(4);
    plot.drawCurve(x, std::cos(x)).label("cos(x)").lineWidth(2);

    Figure figure = {{plot}};
    Canvas canvas = {{figure}};
    canvas.autoclean(false);
    canvas.size(640, 480);

    // 公开 API: 写 gnuplot 脚本并导出绘图数据文件
    canvas.save("consumer_check.svg");

    // 可观察产物校验: 数据文件 plot0.dat 应含 ≥ 90 个 "x y" 数据行（100 个 linspace 点，除注释头）
    if (!exists("plot0.dat"))
    {
        std::printf("FAIL: plot0.dat not created\n");
        return 1;
    }
    int rows = data_rows("plot0.dat");
    std::printf("plot0.dat data rows=%d\n", rows);
    if (rows < 90)
    {
        std::printf("FAIL: expected >= 90 data rows, got %d\n", rows);
        return 1;
    }

    // 可观察产物校验: gnuplot 脚本 multishow0.plt 应已生成
    if (!exists("multishow0.plt"))
    {
        std::printf("FAIL: multishow0.plt not created\n");
        return 1;
    }

    // 公开 API 数值正确性: 验证 sin 曲线的数据值在合理范围（-1,1）内
    std::ifstream d("plot0.dat");
    std::string l;
    bool sin_ok = true;
    double xv, yv;
    while (std::getline(d, l))
    {
        if (!l.empty() && l[0] == '#')
            continue;
        std::istringstream ss(l);
        if (ss >> xv >> yv)
        {
            if (yv < -1.0 || yv > 1.0)
                sin_ok = false;
        }
    }
    if (!sin_ok)
    {
        std::printf("FAIL: curve y values out of expected range\n");
        return 1;
    }

    std::printf("CONSUMER_TEST PASS: sciplot public API plot/save verified\n");
    return 0;
}
