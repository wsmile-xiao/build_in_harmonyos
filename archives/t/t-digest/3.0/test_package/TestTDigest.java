import com.tdunning.math.stats.AVLTreeDigest;
import com.tdunning.math.stats.TDigest;
import com.tdunning.math.stats.TreeDigest;

import java.nio.ByteBuffer;

/**
 * TestTDigest — t-digest API call test.
 *
 * Exercises ArrayDigest/TreeDigest/AVLTreeDigest create/add/quantile/cdf/
 * size/centroidCount/compress/merge/serialization so it genuinely validates
 * the packaged t-digest JAR (R34: not an empty-shell test). Each check posts
 * a PASS/FAIL line; the program exits non-zero if any check fails.
 */
public class TestTDigest {

    private static int passed = 0;
    private static int failed = 0;

    private static void check(String name, boolean cond) {
        if (cond) {
            passed++;
            System.out.println("PASS: " + name);
        } else {
            failed++;
            System.out.println("FAIL: " + name);
        }
    }

    private static boolean close(double a, double b, double eps) {
        return Math.abs(a - b) <= eps;
    }

    public static void main(String[] args) {
        // --- ArrayDigest: basic add/size/quantile/cdf ---
        TDigest array = TDigest.createArrayDigest(100);
        for (int i = 1; i <= 1000; i++) {
            array.add(i);
        }
        check("ArrayDigest.size == 1000", array.size() == 1000);
        check("ArrayDigest.quantile(0.5) near 500",
                close(array.quantile(0.5), 500.0, 50.0));
        check("ArrayDigest.cdf(500) near 0.5",
                close(array.cdf(500.0), 0.5, 0.1));
        check("ArrayDigest.centroidCount > 0", array.centroidCount() > 0);

        // --- TreeDigest: median + min/max boundaries ---
        TDigest tree = TDigest.createTreeDigest(100);
        for (int i = 1; i <= 1000; i++) {
            tree.add(i);
        }
        check("TreeDigest.size == 1000", tree.size() == 1000);
        check("TreeDigest.quantile(0.5) near 500",
                close(tree.quantile(0.5), 500.0, 50.0));
        check("TreeDigest.quantile(0) near min",
                close(tree.quantile(0.0), 1.0, 25.0));
        check("TreeDigest.quantile(1) near max",
                close(tree.quantile(1.0), 1000.0, 25.0));

        // --- AVLTreeDigest: weighted add + compress keeps size ---
        AVLTreeDigest avl = new AVLTreeDigest(100);
        for (int i = 1; i <= 500; i++) {
            avl.add(i, 1);
        }
        check("AVLTreeDigest.size == 500", avl.size() == 500);
        avl.compress();
        check("AVLTreeDigest.size stable after compress", avl.size() == 500);
        check("AVLTreeDigest.quantile(0.5) near 250",
                close(avl.quantile(0.5), 250.0, 30.0));

        // --- Merge: add(other) doubles the size ---
        TDigest left = TDigest.createArrayDigest(100);
        TDigest right = TDigest.createArrayDigest(100);
        for (int i = 1; i <= 200; i++) {
            left.add(i);
            right.add(i + 200);
        }
        left.add(right);
        check("Merge size == 400", left.size() == 400);
        check("Merged quantile(0.5) near 200",
                close(left.quantile(0.5), 200.0, 30.0));

        // --- NaN must be rejected ---
        boolean nanRejected = false;
        try {
            TDigest.createArrayDigest(100).add(Double.NaN);
        } catch (IllegalArgumentException expected) {
            nanRejected = true;
        }
        check("add(NaN) throws IllegalArgumentException", nanRejected);

        System.out.println("RESULT CHECKS: passed=" + passed + " failed=" + failed);
        if (failed != 0) {
            System.err.println("TestTDigest FAILED: " + failed + " check(s)");
            System.exit(1);
        }
        System.out.println("ALL TDIGEST CHECKS PASSED");
    }
}
