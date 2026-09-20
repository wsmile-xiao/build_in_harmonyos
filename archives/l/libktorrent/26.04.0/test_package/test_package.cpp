/* Consumer-side smoke test for libktorrent 26.04.0 (KTorrent6 library).
 *
 * Exercises the public API surface without touching the network:
 *  - bt::GetVersionString() / bt::SetClientInfo() (version.h public API)
 *  - bencode encode/decode round-trip (BEncoder + BDecoder + BDictNode,
 *    the codec every .torrent file goes through)
 *  - SHA-1 hashing (bt::SHA1Hash::generate, used by every torrent hash)
 *
 * Runs headless: libktorrent is a plain library, these entry points
 * need no QApplication.
 */
#include <QBuffer>
#include <QByteArray>
#include <QCoreApplication>
#include <cstdio>

#include <version.h>
#include <bcodec/bdecoder.h>
#include <bcodec/bencoder.h>
#include <bcodec/bnode.h>
#include <util/sha1hash.h>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // 1) library version + client info (version.h public API)
    printf("libktorrent version: %s\n", qPrintable(bt::GetVersionString()));
    bt::SetClientInfo(QString::fromLatin1("ohpcd-smoke"), bt::GetVersionString(),
                      QString::fromLatin1("OS"));

    // 2) bencode round trip: encode {os: harmony, line: 626} then decode
    QByteArray wire;
    QBuffer buf(&wire);
    buf.open(QIODevice::WriteOnly);
    {
        bt::BEncoder enc(&buf);
        enc.beginDict();
        enc.write(QByteArray("os"), QByteArray("harmony"));
        enc.write(QByteArray("line"), (bt::Uint64)626);
        enc.end();
    }
    buf.close();
    printf("bencode encoded %d bytes\n", (int)wire.size());

    bt::BDecoder dec(wire, false, 0);
    std::unique_ptr<bt::BDictNode> dict = dec.decodeDict();
    if (!dict) {
        printf("FAIL: BDecoder::getDict returned null\n");
        return 1;
    }
    QByteArray os = dict->getByteArray(QByteArray("os"));
    qint64 line = dict->getInt64(QByteArray("line"));
    if (os != "harmony" || line != 626) {
        printf("FAIL: bencode round-trip mismatch (os=%s line=%lld)\n",
               os.constData(), (long long)line);
        return 1;
    }
    printf("bencode round-trip: OK (os=%s line=%lld)\n", os.constData(),
           (long long)line);

    // 3) SHA-1 hash (used by every torrent piece hash)
    bt::SHA1Hash h = bt::SHA1Hash::generate((const bt::Uint8 *)"ohpcd", 5);
    printf("sha1(ohpcd) = %s\n", qPrintable(h.toString()));

    // 4) GetClientInfo / PeerIDPrefix round trip
    QString pfx = bt::PeerIDPrefix();
    if (pfx.size() < 2) {
        printf("FAIL: PeerIDPrefix too short: %s\n", qPrintable(pfx));
        return 1;
    }
    printf("peer id prefix: %s\n", qPrintable(pfx));
    printf("all checks passed\n");
    return 0;
}
