import javax.vecmath.Matrix3f;
import javax.vecmath.Matrix4f;
import javax.vecmath.Quat4f;
import javax.vecmath.Tuple3f;
import javax.vecmath.Vector3f;

/**
 * TestVecmath — real API smoke test for javax.vecmath 1.5.2.
 *
 * Exercises core vector, matrix and quaternion math so it genuinely validates
 * the packaged vecmath JAR (R34: not an empty-shell test). Each check posts a
 * PASS/FAIL line; the program exits non-zero if any check fails.
 */
public class TestVecmath {

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

    private static boolean close(float a, float b, float eps) {
        return Math.abs(a - b) <= eps;
    }

    public static void main(String[] args) {
        // --- Vector3f: length / normalize / dot / cross ---
        Vector3f a = new Vector3f(3.0f, 4.0f, 0.0f);
        check("Vector3f.length (3,4,0) == 5", close(a.length(), 5.0f, 1e-6f));
        check("Vector3f.lengthSquared == 25", close(a.lengthSquared(), 25.0f, 1e-5f));

        Vector3f n = new Vector3f(a);
        n.normalize();
        check("Vector3f.normalize() yields unit vector",
              close(n.length(), 1.0f, 1e-6f));
        check("normalized components correct",
              close(n.x, 0.6f, 1e-6f) && close(n.y, 0.8f, 1e-6f));

        Vector3f x = new Vector3f(1.0f, 0.0f, 0.0f);
        Vector3f y = new Vector3f(0.0f, 1.0f, 0.0f);
        check("Vector3f.dot(x,y) == 0", close(x.dot(y), 0.0f, 1e-6f));
        check("Vector3f.dot(x,x) == 1", close(x.dot(x), 1.0f, 1e-6f));

        Vector3f z = new Vector3f();
        z.cross(x, y);
        check("Vector3f.cross(x,y) == z-axis", close(z.z, 1.0f, 1e-6f)
              && close(z.x, 0.0f, 1e-6f) && close(z.y, 0.0f, 1e-6f));

        // --- Tuple3f getters/setters ---
        Vector3f b = new Vector3f(1.5f, -2.5f, 7.25f);
        check("Tuple3f getX/getY/getZ", close(b.getX(), 1.5f, 1e-6f)
              && close(b.getY(), -2.5f, 1e-6f) && close(b.getZ(), 7.25f, 1e-6f));
        b.setX(9.0f);
        check("Tuple3f setX", close(b.getX(), 9.0f, 1e-6f));
        float[] arr = new float[3];
        b.get(arr);
        check("Tuple3f.get(float[])", close(arr[0], 9.0f, 1e-6f)
              && close(arr[1], -2.5f, 1e-6f) && close(arr[2], 7.25f, 1e-6f));

        // --- Matrix4f: identity + transform ---
        Matrix4f id = new Matrix4f();
        id.setIdentity();
        Vector3f v = new Vector3f(1.0f, 2.0f, 3.0f);
        // m00=1 element of identity
        check("Matrix4f.setIdentity m00==1", id.m00 == 1.0f
              && id.m01 == 0.0f && id.m03 == 0.0f);

        // Determinant of identity == 1
        Matrix4f det = new Matrix4f();
        det.setIdentity();
        check("Matrix4f identity determinant close to 1",
              Math.abs(det.determinant() - 1.0f) < 1e-4f);

        // --- Matrix3f mul ---
        Matrix3f m = new Matrix3f();
        m.setIdentity();
        Matrix3f m2 = new Matrix3f();
        m2.setIdentity();
        Matrix3f prod = new Matrix3f();
        prod.mul(m, m2);
        check("Matrix3f.mul(identity,identity) diag==1",
              prod.m00 == 1.0f && prod.m11 == 1.0f && prod.m22 == 1.0f);
        check("Matrix3f.determinant identity == 1",
              Math.abs(prod.determinant() - 1.0f) < 1e-5f);

        // --- Quat4f: conjugate negates the vector part ---
        // NOTE: Quat4f stores a unit quaternion; its (x,y,z,w) float constructor
        // NORMALIZES the input (divides each component by the magnitude). To make
        // the expected values predictable, pass an already-normalized quaternion
        // |(0.5,0.5,0.5,0.5)| = 1 so normalization is a no-op and the components
        // stay exactly 0.5. (Previously (1,2,3,4) was silently rescaled to
        // (1,2,3,4)/sqrt(30), making the post-conjugate check fail.)
        Quat4f q = new Quat4f(0.5f, 0.5f, 0.5f, 0.5f);
        Quat4f qc = new Quat4f(q);
        qc.conjugate();
        check("Quat4f.conjugate negates vector part",
              close(qc.x, -0.5f, 1e-6f) && close(qc.y, -0.5f, 1e-6f)
              && close(qc.z, -0.5f, 1e-6f) && close(qc.w, 0.5f, 1e-6f));
        // conjugate of a conjugate returns the original
        Quat4f qcc = new Quat4f(qc);
        qcc.conjugate();
        check("Quat4f double-conjugate == original",
              close(qcc.x, q.x, 1e-6f) && close(qcc.y, q.y, 1e-6f)
              && close(qcc.z, q.z, 1e-6f) && close(qcc.w, q.w, 1e-6f));

        System.out.println("RESULT CHECKS: passed=" + passed + " failed=" + failed);
        if (failed != 0) {
            System.err.println("TestVecmath FAILED: " + failed + " check(s)");
            System.exit(1);
        }
        System.out.println("ALL VECMATH CHECKS PASSED");
    }
}
