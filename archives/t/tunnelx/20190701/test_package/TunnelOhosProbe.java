package Tunnel;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/**
 * Consumer-side probe for the packaged tunnelx JAR on HarmonyOS (OHOS).
 *
 * The probe lives in package {@code Tunnel} on purpose: tunnelx ships every
 * class as package-private, so a probe inside the same package is the only way
 * to assert that the packaged bytecode really is the intended upstream
 * snapshot.  It is compiled in test_package/test.sh with the very same JVM the
 * package consumer uses, and it never touches AWT/Swing windows, so it runs on
 * a headless HarmonyOS PC.
 *
 * Output contract (parsed by test.sh): each line is
 * {@code PROBE PASS <id> | <what> | <detail>} or {@code PROBE FAIL ...}.
 */
public final class TunnelOhosProbe {

    private static int passed = 0;
    private static final List<String> failed = new ArrayList<String>();

    private TunnelOhosProbe() {
    }

    private static void check(String id, String what, boolean ok, String detail) {
        if (ok) {
            passed++;
            System.out.println("PROBE PASS " + id + " | " + what + " | " + detail);
        } else {
            failed.add(id);
            System.out.println("PROBE FAIL " + id + " | " + what + " | " + detail);
        }
    }

    private static List<String> lines(InputStream in) throws Exception {
        List<String> out = new ArrayList<String>();
        if (in == null) {
            return out;
        }
        BufferedReader reader = new BufferedReader(
                new InputStreamReader(in, StandardCharsets.UTF_8));
        try {
            String line;
            while ((line = reader.readLine()) != null) {
                String trimmed = line.trim();
                if (trimmed.length() > 0) {
                    out.add(trimmed);
                }
            }
        } finally {
            reader.close();
        }
        return out;
    }

    public static void main(String[] args) throws Exception {
        ClassLoader loader = TunnelOhosProbe.class.getClassLoader();

        String osName = System.getProperty("os.name", "");
        String osArch = System.getProperty("os.arch", "");
        String javaHome = System.getProperty("java.home", "");
        String tmpDir = System.getProperty("java.io.tmpdir", "");

        // ── OHOS-1: the package runs on the HarmonyOS aarch64 JVM ──────────
        check("OHOS-1", "HarmonyOS aarch64 JVM",
                "aarch64".equals(osArch)
                        && ("HarmonyOS".equals(osName)
                            || "Linux".equals(osName)
                            || "OHOS".equals(osName))
                        && javaHome.length() > 0,
                "os.name=" + osName + ", os.arch=" + osArch
                        + ", java.home=" + javaHome);

        // ── OHOS-2: HarmonyOS has no writable /tmp ────────────────────────
        // src/FileAbstraction.java:136-142 resolves the scratch directory as
        // <cwd>/tmp -> ~/.tunnelx/tmp/ -> java.io.tmpdir; on HarmonyOS the
        // last resort must not be "/tmp", hence the launcher's
        // -Djava.io.tmpdir=<writable dir>.
        check("OHOS-2", "java.io.tmpdir redirected away from read-only /tmp",
                tmpDir.length() > 0 && !"/tmp".equals(tmpDir),
                "java.io.tmpdir=" + tmpDir);

        // ── PKG-1: packaged classes are the intended upstream snapshot ────
        check("PKG-1", "upstream version marker",
                "version2019-07-01 DoES".equals(TN.tunnelversion),
                "TN.tunnelversion=" + TN.tunnelversion);

        // ── PKG-2..4: self-contained resources ────────────────────────────
        // Resolved exactly like src/FileAbstraction.java:146-160, i.e. through
        // the class loader, which is the path used when the application is
        // started from the JAR with no symbols/ directory on disk.
        List<String> symbols = lines(loader.getResourceAsStream("symbols/listdir.txt"));
        check("PKG-2", "symbols/listdir.txt bundled",
                symbols.size() == 38
                        && symbols.contains("mud.xml")
                        && symbols.contains("curtain.xml")
                        && symbols.contains("helpfile.md"),
                "entries=" + symbols.size() + " (expected 38: 37 symbol files + listdir.txt)");

        List<String> tutorials = lines(loader.getResourceAsStream("tutorials/listdir.txt"));
        check("PKG-3", "tutorials/listdir.txt bundled",
                tutorials.size() == 8
                        && tutorials.contains("010_lesson_one.xml")
                        && tutorials.contains("810_scalebars.xml"),
                "entries=" + tutorials.size() + " (expected 8: 7 tutorials + listdir.txt)");

        List<String> help = lines(loader.getResourceAsStream("symbols/helpfile.md"));
        check("PKG-4", "symbols/helpfile.md bundled",
                !help.isEmpty(),
                "lines=" + help.size());

        // ── PKG-5: upstream geometry kernel is executable ─────────────────
        Vec3d a = new Vec3d(1.0, 2.0, 3.0);
        Vec3d b = new Vec3d(0.5, 0.25, -1.0);
        a.PlusEquals(b);
        a.TimesEquals(2.0);
        boolean geometryOk = Math.abs(a.x - 3.0) < 1e-12
                && Math.abs(a.y - 4.5) < 1e-12
                && Math.abs(a.z - 4.0) < 1e-12;
        check("PKG-5", "upstream Vec3d geometry kernel",
                geometryOk, "Vec3d(1,2,3)+(0.5,0.25,-1)*2 = " + a.toString());

        System.out.println("PROBE SUMMARY passed=" + passed
                + " failed=" + failed.size()
                + (failed.isEmpty() ? "" : " failed_ids=" + failed));
        if (!failed.isEmpty()) {
            System.exit(1);
        }
    }
}
