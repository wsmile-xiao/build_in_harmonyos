// Test: verify that the QMobipocket6 library is usable.
// Creates a Mobipocket::Document from an empty QBuffer and checks
// that it correctly reports as invalid (no valid Mobipocket data).
#include <QBuffer>
#include <QByteArray>
#include <qmobipocket/mobipocket.h>

int main()
{
    QByteArray emptyData;
    QBuffer buffer(&emptyData);
    buffer.open(QIODevice::ReadOnly);

    Mobipocket::Document doc(&buffer);
    // An empty buffer does not contain a valid Mobipocket document.
    // If isValid() returns true, something is wrong.
    if (doc.isValid()) {
        return 1;
    }
    // hasDRM() should also be false for an invalid document.
    if (doc.hasDRM()) {
        return 2;
    }
    return 0;
}
