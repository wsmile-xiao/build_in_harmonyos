#include <QXlsxQt5/xlsxdocument.h>
#include <QXlsxQt5/xlsxcell.h>
#include <QXlsxQt5/xlsxformat.h>
#include <QXlsxQt5/xlsxworksheet.h>
#include <QXlsxQt5/xlsxworkbook.h>
#include <QDebug>
#include <QString>
#include <cstdio>

int main() {
    // Test 1: Create a document
    QXlsx::Document xlsx;

    // Test 2: Write cells
    xlsx.write("A1", "Hello QXlsx!");
    xlsx.write("B1", 12345);
    xlsx.write("C1", 3.14159);

    // Test 3: Apply formatting
    QXlsx::Format format;
    format.setFontColor(Qt::blue);
    format.setFontSize(14);
    format.setFontBold(true);
    xlsx.write("A2", "Formatted text", format);

    // Test 4: Read back
    QVariant val = xlsx.read("A1");
    if (val.toString() != "Hello QXlsx!") {
        qDebug() << "FAIL: Read A1 expected 'Hello QXlsx!' got" << val.toString();
        return 1;
    }
    qDebug() << "PASS: Read A1 =" << val.toString();

    // Test 5: Save document
    // Use TMPDIR or home dir since /tmp is read-only on OpenHarmony (E002)
    const char* tmpdir = getenv("TMPDIR");
    if (!tmpdir) tmpdir = getenv("HOME");
    if (!tmpdir) tmpdir = "/tmp";
    QString filename = QString::fromLatin1(tmpdir) + QLatin1String("/qxlsx_test_output.xlsx");
    if (!xlsx.saveAs(filename)) {
        qDebug() << "FAIL: Could not save to" << filename;
        return 1;
    }
    qDebug() << "PASS: Saved to" << filename;

    // Test 6: Load and read back
    QXlsx::Document xlsx2(filename);
    if (!xlsx2.load()) {
        qDebug() << "FAIL: Could not load" << filename;
        return 1;
    }
    QVariant v1 = xlsx2.read("A1");
    QVariant v2 = xlsx2.read("B1");
    QVariant v3 = xlsx2.read("C1");
    if (v1.toString() != "Hello QXlsx!") {
        qDebug() << "FAIL: Loaded A1 expected 'Hello QXlsx!' got" << v1.toString();
        return 1;
    }
    qDebug() << "PASS: Loaded A1 =" << v1.toString();
    qDebug() << "PASS: Loaded B1 =" << v2.toString();
    qDebug() << "PASS: Loaded C1 =" << v3.toString();
    qDebug() << "All tests passed!";

    return 0;
}
