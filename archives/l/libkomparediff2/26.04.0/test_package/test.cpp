// Consumer smoke test for libkomparediff2 26.04.0.
//
// Exercises the public KompareDiff2::DiffModel / Difference API the same way
// upstream InteractiveDiffTest::testOneLineChange does: create a programmatic
// one-line change, verify the parsed Difference, and check the
// recreateDiff()/apply bookkeeping. No external diff binary or display is
// needed (DiffModel uses Q_OBJECT/QCoreApplication only).
#include <QCoreApplication>
#include <QStringList>

#include <KompareDiff2/DiffModel>
#include <KompareDiff2/Difference>

using namespace KompareDiff2;

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

    // 1) Programmatic one-line change (upstream testOneLineChange scenario).
    DiffModel model;
    model.linesChanged(QStringList() << QStringLiteral("oldline\n"),
                       QStringList() << QStringLiteral("newline\n"), 2);
    if (model.differenceCount() != 1) {
        return 1;
    }
    const Difference *diff = model.differenceAt(0);
    if (diff->type() != int(Difference::Change)) {
        return 2;
    }

    // 2) recreateDiff() must serialize the stored difference.
    if (model.recreateDiff().isEmpty()) {
        return 3;
    }

    // 3) Applied/unapplied bookkeeping via the public API.
    model.applyAllDifferences(true);
    if (!model.differenceAt(0)->applied()) {
        return 4;
    }
    model.applyAllDifferences(false);
    if (model.differenceAt(0)->applied()) {
        return 5;
    }

    return 0;
}
