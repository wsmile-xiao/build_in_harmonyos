#include <KTextTemplate/Context>
#include <KTextTemplate/Engine>
#include <KTextTemplate/Template>
#include <cstdio>
#include <QString>

int main() {
    KTextTemplate::Engine engine;
    KTextTemplate::Context context;
    context.insert(QStringLiteral("name"), QStringLiteral("Akonadi"));

    auto templ = engine.newTemplate(QStringLiteral("Hello {{ name }}"), QStringLiteral("smoke"));
    if (!templ || templ->error()) {
        std::fprintf(stderr, "FAIL: template parse error\n");
        return 1;
    }

    const QString rendered = templ->render(&context);
    if (rendered != QStringLiteral("Hello Akonadi")) {
        std::fprintf(stderr, "FAIL: unexpected render output\n");
        return 1;
    }

    std::printf("PASS: KTextTemplate rendered %s\n", rendered.toUtf8().constData());
    std::printf("PASS: KTextTemplate context variable resolved\n");
    return 0;
}
