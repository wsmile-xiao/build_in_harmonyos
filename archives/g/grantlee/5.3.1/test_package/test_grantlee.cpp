/* test_package —— grantlee 消费者测试（Conan L1 / R34）。
 *
 * 真实调用被测包公开 API（Grantlee5::Templates 核心链路）：
 *   Engine/Template 加载 → Context 注入 → 渲染 → 结果断言
 * 覆盖：变量插值（{{ name }}）、过滤器链（{{ names.size }} 等内建）、
 *       {% for %} 标签、模板字符串直渲（Template Inclusion）。
 * 断言失败返回非零，conan create 的 test() 即失败。
 */
#include <QCoreApplication>
#include <QDebug>
#include <QDir>
#include <QStringList>

#include <grantlee/engine.h>
#include <grantlee/templateloader.h>

#include <cstdio>

static int g_fail = 0;

#define CHECK(desc, cond)                                     \
    do                                                        \
    {                                                         \
        if (cond)                                             \
        {                                                     \
            std::printf("PASS %d: %s\n", __LINE__, desc);     \
        }                                                     \
        else                                                  \
        {                                                     \
            std::printf("FAIL %d: %s\n", __LINE__, desc);     \
            g_fail++;                                         \
        }                                                     \
    } while (0)

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    Grantlee::Engine *engine = new Grantlee::Engine(nullptr);

    /* 标签插件目录注入：GRANTLEE_PLUGIN_PATH 宏在库内烧录的是构建机
     * install 路径，交叉产物需要运行时注入——测试通过 addPluginPath
     * 指到 conan 包内插件根（由 test_package/conanfile.py 写入
     * GRANTLEE_TEST_PLUGIN_DIR 环境变量）；引擎在该目录下按
     * /grantlee/<major>.<minor>/ 布局查找（engine.cpp
     * EnginePrivate::loadCppLibrary）。消费者集成同法。 */
    const QString pluginDir =
        QString::fromLocal8Bit(qgetenv("GRANTLEE_TEST_PLUGIN_DIR"));
    if (!pluginDir.isEmpty()) {
        engine->addPluginPath(pluginDir + QStringLiteral("/"));
        std::printf("plugin dir: %s\n", qPrintable(pluginDir));
        const auto libs = engine->pluginPaths();
        for (const auto &p : libs)
            std::printf("  engine plugin path: %s\n", qPrintable(p));
    }

    /* ── 用例 1：变量插值 + HTML 转义（autoescape）── */
    Grantlee::Template t1 = engine->newTemplate(
        QString::fromLatin1("Hello {{ name }}!"), QStringLiteral("t1"));
    Grantlee::Context c1;
    c1.insert(QStringLiteral("name"), QStringLiteral("Grantlee"));
    QString out1 = t1->render(&c1);
    CHECK("variable interpolation renders",
          out1 == QString::fromLatin1("Hello Grantlee!"));

    /* ── 用例 2：HTML 特殊字符自动转义（SafeString 语义）── */
    Grantlee::Template t2 = engine->newTemplate(
        QString::fromLatin1("{{ markup }}"), QStringLiteral("t2"));
    Grantlee::Context c2;
    c2.insert(QStringLiteral("markup"), QString::fromLatin1("<b>&"));
    QString out2 = t2->render(&c2);
    CHECK("autoescape escapes html entities",
          out2 == QString::fromLatin1("&lt;b&gt;&amp;"));

    /* ── 用例 3：{% for %} 循环标签 + 列表上下文 ── */
    Grantlee::Template t3 = engine->newTemplate(
        QString::fromLatin1("{% for item in items %}{{ item }};{% endfor %}"),
        QStringLiteral("t3"));
    QStringList items;
    items << QStringLiteral("a") << QStringLiteral("b") << QStringLiteral("c");
    Grantlee::Context c3;
    c3.insert(QStringLiteral("items"), items);
    QString out3 = t3->render(&c3);
    CHECK("for tag iterates list context",
          out3 == QString::fromLatin1("a;b;c;"));

    /* ── 用例 4：内建过滤器（upper）── */
    Grantlee::Template t4 = engine->newTemplate(
        QString::fromLatin1("{{ name|upper }}"), QStringLiteral("t4"));
    Grantlee::Context c4;
    c4.insert(QStringLiteral("name"), QStringLiteral("ohos"));
    QString out4 = t4->render(&c4);
    CHECK("builtin filter upper works",
          out4 == QString::fromLatin1("OHOS"));

    /* ── 用例 5：错误处理——未闭合标签（上游语义：错误经 qWarning 输出
     *    到 stderr（grantlee.template 前缀），渲染返回空串——与上游
     *    Qt 惯例一致。断言"不崩溃且返回可控空结果"）── */
    Grantlee::Template t5 = engine->newTemplate(
        QString::fromLatin1("{% for x in y %}"), QStringLiteral("t5"));
    Grantlee::Context c5;
    QString out5 = t5->render(&c5);
    CHECK("unclosed tag yields controlled empty output (error via stderr)",
          out5.isEmpty());

    std::printf("total failures = %d\n", g_fail);
    return g_fail ? 1 : 0;
}
