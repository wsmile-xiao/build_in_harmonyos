import com.peterabeles.auto64fto32f.AugmentJavaFiles;
import com.peterabeles.auto64fto32f.ConvertFile32From64;
import com.peterabeles.auto64fto32f.Language;
import com.peterabeles.auto64fto32f.RecursiveConvert;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Scanner;

/**
 * Consumer-side functional test (R34): exercises the packaged
 * auto64fto32f JAR through its real public API.
 *
 * 6 checks:
 *  1. AugmentJavaFiles.augment() inserts javax.annotation.Generated import + annotation
 *  2. augment() is idempotent for already-generated files
 *  3. ConvertFile32From64.process() default replacements:
 *     double-to-float, _F64-to-_F32 rename, literal f-suffix, Math. cast,
 *     and the exempt-marker token override
 *  4. //CUSTOM ignore keeps a token untouched
 *  5. RecursiveConvert.process() end-to-end F64 -> F32 file generation
 *  6. Language enum suffix mapping (java/kt)
 */
public class TestAuto64Fto32F {
    private static int total = 0;
    private static int passed = 0;

    private static void check(String name, boolean ok, String detail) {
        total++;
        if (ok) {
            passed++;
            System.out.println("PASS " + name);
        } else {
            System.out.println("FAIL " + name + " :: " + detail);
        }
    }

    private static String streamToString(InputStream in) {
        return new Scanner(in).useDelimiter("\\A").next();
    }

    public static void main(String[] args) throws Exception {
        // ---- Check 1: augment adds @Generated to a plain class ----
        String input1 = "package dummy;\n" +
                "import foobar;\n" +
                "/** Going to mention the word class here to mess things up */\n" +
                "public class DummyCode_F64 {}\n";
        InputStream out1 = new AugmentJavaFiles().augment(
                new ByteArrayInputStream(input1.getBytes(StandardCharsets.UTF_8)),
                "DummyCode_F64");
        String got1 = streamToString(out1);
        check("augment_adds_generated_annotation",
                got1.contains("import javax.annotation.Generated;")
                        && got1.contains("@Generated(\"dummy.DummyCode_F64\")")
                        && got1.contains("public class DummyCode_F64 {}"),
                got1);

        // ---- Check 2: augment is idempotent when already generated ----
        String input2 = "package dummy;\n" +
                "import javax.annotation.Generated;\n" +
                "import foobar;\n" +
                "@Generated(\"dummy.DummyCode_F64\")\n" +
                "public interface DummyCode_F64 {}\n";
        InputStream out2 = new AugmentJavaFiles().augment(
                new ByteArrayInputStream(input2.getBytes(StandardCharsets.UTF_8)),
                "DummyCode_F64");
        check("augment_idempotent",
                input2.equals(streamToString(out2)),
                "output differs from input for already-generated source");

        // ---- Check 3: default conversion semantics on a real file pair ----
        File dir3 = Files.createTempDirectory("a64f_conv").toFile();
        File in3 = new File(dir3, "ConvDemo_F64.java");
        String src3 = "package demo;\n" +
                "public class ConvDemo_F64 {\n" +
                "\tdouble foo = 1.6*bar + Math.exp(6);\n" +
                "\t/**/double keepMe = 0.5;\n" +
                "}\n";
        Files.write(in3.toPath(), src3.getBytes(StandardCharsets.UTF_8));
        File outF3 = new File(dir3, "ConvDemo_F32.java");
        new ConvertFile32From64(true).process(in3, outF3);
        String got3 = new String(Files.readAllBytes(outF3.toPath()),
                StandardCharsets.UTF_8);
        check("convert_default_replacements",
                got3.contains("class ConvDemo_F32")
                        && got3.contains("float foo = 1.6f*bar + (float)Math.exp(6);")
                        && got3.contains("/**/double keepMe = 0.5f;"),
                got3);

        // ---- Check 4: //CUSTOM ignore leaves the named token alone ----
        File dir4 = Files.createTempDirectory("a64f_cust").toFile();
        File in4 = new File(dir4, "CustDemo_F64.java");
        String src4 = "//CUSTOM ignore Keep_F64\n" +
                "public class CustDemo_F64 {\n" +
                "\tdouble d = 1.5;\n" +
                "\tdouble x = Keep_F64 .value;\n" +
                "}\n";
        Files.write(in4.toPath(), src4.getBytes(StandardCharsets.UTF_8));
        File outF4 = new File(dir4, "CustDemo_F32.java");
        new ConvertFile32From64(true).process(in4, outF4);
        String got4 = new String(Files.readAllBytes(outF4.toPath()),
                StandardCharsets.UTF_8);
        check("convert_custom_ignore",
                got4.contains("class CustDemo_F32")
                        && got4.contains("float d = 1.5f;")
                        && got4.contains("Keep_F64")
                        && !got4.contains("Keep_F32"),
                got4);

        // ---- Check 5: RecursiveConvert end-to-end directory sweep ----
        File dir5 = Files.createTempDirectory("a64f_rec").toFile();
        File in5 = new File(dir5, "Sample_F64.java");
        String src5 = "/**\n" +
                " * Sample copyright header.\n" +
                " */\n" +
                "public class Sample_F64 {\n" +
                "\tdouble x = 2.5;\n" +
                "}\n";
        Files.write(in5.toPath(), src5.getBytes(StandardCharsets.UTF_8));
        new RecursiveConvert(new ConvertFile32From64(true)).process(dir5);
        File outF5 = new File(dir5, "Sample_F32.java");
        boolean exists5 = outF5.isFile();
        String got5 = exists5
                ? new String(Files.readAllBytes(outF5.toPath()), StandardCharsets.UTF_8)
                : "<missing>";
        check("recursive_convert_generates_f32_file",
                exists5 && got5.contains("class Sample_F32")
                        && got5.contains("float x = 2.5f;")
                        && got5.contains("Sample copyright header"),
                got5);

        // ---- Check 6: Language enum suffixes ----
        check("language_suffix_mapping",
                Language.JAVA.suffix().equals("java")
                        && Language.KOTLIN.suffix().equals("kt"),
                "JAVA=" + Language.JAVA.suffix()
                        + " KOTLIN=" + Language.KOTLIN.suffix());

        System.out.println("AUTO64FTO32F_TEST_PASS " + passed + "/" + total);
        if (passed != total) {
            System.exit(1);
        }
    }
}
