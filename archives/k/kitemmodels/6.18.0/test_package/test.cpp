// kitemmodels 6.18.0 consumer test (R34: exercises real API).
// Creates a KNumberModel and verifies row count and values.
#include <KNumberModel>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    KNumberModel model;
    model.setMinimumValue(1.0);
    model.setMaximumValue(3.0);
    model.setStepSize(1.0);

    if (model.rowCount() != 3) {
        std::printf("FAIL: rowCount=%d, expected 3\n", model.rowCount());
        return 1;
    }

    const QModelIndex index = model.index(1, 0);
    if (!index.isValid()) {
        std::printf("FAIL: index(1,0) is invalid\n");
        return 1;
    }

    const double value = model.data(index, KNumberModel::ValueRole).toDouble();
    if (value != 2.0) {
        std::printf("FAIL: value=%f, expected 2.0\n", value);
        return 1;
    }

    std::printf("PASS: KNumberModel rowCount/value OK\n");
    return 0;
}
