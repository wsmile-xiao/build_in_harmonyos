import com.google.zxing.BarcodeFormat;
import com.google.zxing.BinaryBitmap;
import com.google.zxing.DecodeHintType;
import com.google.zxing.MultiFormatReader;
import com.google.zxing.MultiFormatWriter;
import com.google.zxing.Result;
import com.google.zxing.RGBLuminanceSource;
import com.google.zxing.common.BitMatrix;
import com.google.zxing.common.HybridBinarizer;
import com.google.zxing.qrcode.QRCodeWriter;
import com.google.zxing.qrcode.decoder.Version;

/**
 * Consumer checks for the packaged zxing core JAR.
 *
 * Every assertion below runs against lib/zxing-core-3.5.3.jar taken from the
 * Conan package (not from the build tree) and prints a single machine-readable
 * summary line that test.py compares byte for byte.
 */
public final class TestZxingCore {

    private static int checks = 0;

    private static void check(boolean condition, String what) {
        checks++;
        if (!condition) {
            throw new IllegalStateException("FAILED #" + checks + ": " + what);
        }
    }

    private static void checkEquals(Object expected, Object actual, String what) {
        checks++;
        if (expected == null ? actual != null : !expected.equals(actual)) {
            throw new IllegalStateException(
                "FAILED #" + checks + ": " + what + " expected=" + expected
                    + " actual=" + actual);
        }
    }

    private static Class<?> cls(String name) throws Exception {
        checks++;
        try {
            return Class.forName(name);
        } catch (ClassNotFoundException e) {
            throw new IllegalStateException("FAILED #" + checks + ": missing class " + name, e);
        }
    }

    /** Render a BitMatrix to an ARGB pixel array, exactly like a scanned image. */
    private static int[] toPixels(BitMatrix matrix) {
        int width = matrix.getWidth();
        int height = matrix.getHeight();
        int[] pixels = new int[width * height];
        for (int y = 0; y < height; y++) {
            int offset = y * width;
            for (int x = 0; x < width; x++) {
                pixels[offset + x] = matrix.get(x, y) ? 0xFF000000 : 0xFFFFFFFF;
            }
        }
        return pixels;
    }

    /** Encode with the packaged writer, decode with the packaged reader. */
    private static Result roundTrip(MultiFormatWriter writer, String payload)
        throws Exception {
        BitMatrix matrix = writer.encode(payload, BarcodeFormat.QR_CODE, 320, 320);
        check(matrix.getWidth() > 0 && matrix.getHeight() > 0, "QR matrix dimensions");
        RGBLuminanceSource source =
            new RGBLuminanceSource(matrix.getWidth(), matrix.getHeight(), toPixels(matrix));
        BinaryBitmap bitmap = new BinaryBitmap(new HybridBinarizer(source));
        return new MultiFormatReader().decode(bitmap);
    }

    public static void main(String[] args) throws Exception {
        // --- packaged JAR really is on the class path ---
        cls("com.google.zxing.MultiFormatWriter");
        cls("com.google.zxing.MultiFormatReader");
        cls("com.google.zxing.RGBLuminanceSource");
        cls("com.google.zxing.qrcode.QRCodeWriter");

        // --- public API surface ---
        check(BarcodeFormat.QR_CODE != null, "BarcodeFormat.QR_CODE");
        check(BarcodeFormat.values().length > 0, "BarcodeFormat.values()");
        check(DecodeHintType.values().length > 0, "DecodeHintType.values()");

        // --- QR encode/decode round trip on HarmonyOS PC ---
        MultiFormatWriter writer = new MultiFormatWriter();

        Result first = roundTrip(writer, "HarmonyOS PC zxing 3.5.3");
        checkEquals("HarmonyOS PC zxing 3.5.3", first.getText(), "round trip #1 text");
        checkEquals(BarcodeFormat.QR_CODE, first.getBarcodeFormat(), "round trip #1 format");

        StringBuilder longPayload = new StringBuilder();
        for (int i = 0; i < 16; i++) {
            longPayload.append("zxing-round-trip-").append(i).append(';');
        }
        Result second = roundTrip(writer, longPayload.toString());
        checkEquals(longPayload.toString(), second.getText(), "round trip #2 text");

        Result third = roundTrip(writer, "01234567890123456789");
        checkEquals("01234567890123456789", third.getText(), "round trip #3 text");

        // --- direct writer entry point ---
        BitMatrix direct = new QRCodeWriter().encode("ZXING", BarcodeFormat.QR_CODE, 200, 200);
        check(direct.getWidth() >= 21 && direct.getHeight() >= 21, "QRCodeWriter matrix size");

        // --- QR spec constant readable from the packaged decoder ---
        Version version = Version.getVersionForNumber(1);
        checkEquals(Integer.valueOf(21), Integer.valueOf(version.getDimensionForVersion()),
            "QR version 1 dimension");

        System.out.println("zxing 3.5.3 consumer tests passed: " + checks);
    }
}
