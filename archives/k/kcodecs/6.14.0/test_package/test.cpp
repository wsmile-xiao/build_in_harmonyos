// kcodecs 6.14.0 consumer test (R34: exercises real API).
// Verifies KCodecs can encode/decode base64 via the KCodecs module.
#include <KCodecs>
#include <QByteArray>
#include <cstdio>

int main() {
    const QByteArray in("hello world");
    const QByteArray enc = KCodecs::base64Encode(in);
    const QByteArray dec = KCodecs::base64Decode(enc);
    if (dec != in) {
        std::printf("FAIL: base64 round-trip mismatch: %s\n",
                    dec.constData());
        return 1;
    }
    std::printf("PASS: KCodecs base64 round-trip OK (%s)\n",
                enc.constData());
    return 0;
}
