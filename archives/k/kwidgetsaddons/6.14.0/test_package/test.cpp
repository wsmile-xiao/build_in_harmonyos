// kwidgetsaddons 6.14.0 consumer test (R34: exercises real API).
// Constructs a KPageWidgetModel and verifies addPage/rowCount round-trip.
#include <KPageWidgetModel>
#include <QString>
#include <cstdio>

int main() {
    KPageWidgetModel model;
    KPageWidgetItem *item = model.addPage(nullptr, QStringLiteral("first"));
    if (!item) {
        std::printf("FAIL: addPage returned null item\n");
        return 1;
    }
    if (model.rowCount() != 1) {
        std::printf("FAIL: rowCount=%d, expected 1\n", model.rowCount());
        return 1;
    }
    std::printf("PASS: KPageWidgetModel addPage/rowCount OK (rows=%d)\n",
                model.rowCount());
    return 0;
}
