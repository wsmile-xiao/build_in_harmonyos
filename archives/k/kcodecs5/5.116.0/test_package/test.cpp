// kcodecs5 5.116.0 consumer test (R34: exercises real API).
// Verifies KCodecs base64 encode/decode round trip plus quoted-printable
// and RFC2047 encoded-word handling via the KCodecs module.
#include <KCodecs>
#include <QByteArray>
#include <QString>
#include <cstdio>

static int checkBase64()
{
    const QByteArray in("hello kcodecs5 on harmony");
    const QByteArray enc = KCodecs::base64Encode(in);
    const QByteArray dec = KCodecs::base64Decode(enc);
    if (dec != in) {
        std::printf("FAIL: base64 round-trip mismatch: %s\n",
                    dec.constData());
        return 1;
    }
    std::printf("PASS: base64 round-trip OK (%s)\n", enc.constData());
    return 0;
}

static int checkQuotedPrintable()
{
    const QByteArray in("KCodecs=quoted printable");
    const QByteArray enc = KCodecs::quotedPrintableEncode(in);
    const QByteArray dec = KCodecs::quotedPrintableDecode(enc);
    if (dec != in) {
        std::printf("FAIL: quoted-printable round-trip mismatch: %s\n",
                    dec.constData());
        return 1;
    }
    std::printf("PASS: quoted-printable round-trip OK\n");
    return 0;
}

static int checkRfc2047()
{
    // RFC2047 B-encoded word for "hello" in UTF-8: =?utf-8?B?aGVsbG8=?=
    const QByteArray encoded("=?utf-8?B?aGVsbG8=?=");
    const QString decoded = KCodecs::decodeRFC2047String(
        QString::fromLatin1(encoded));
    if (decoded != QString::fromUtf8("hello")) {
        std::printf("FAIL: RFC2047 decode mismatch: %s\n",
                    decoded.toUtf8().constData());
        return 1;
    }
    std::printf("PASS: RFC2047 decode OK\n");
    return 0;
}

int main() {
    if (checkBase64() != 0) {
        return 1;
    }
    if (checkQuotedPrintable() != 0) {
        return 1;
    }
    if (checkRfc2047() != 0) {
        return 1;
    }
    return 0;
}