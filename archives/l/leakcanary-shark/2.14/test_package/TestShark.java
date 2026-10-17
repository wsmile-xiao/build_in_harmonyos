import shark.ApplicationLeak;
import shark.CloseableHeapGraph;
import shark.GcRoot;
import shark.HeapAnalysis;
import shark.HeapAnalysisSuccess;
import shark.HeapAnalyzer;
import shark.HprofHeader;
import shark.HprofHeapGraph;
import shark.HprofIndex;
import shark.HprofRecord;
import shark.HprofVersion;
import shark.HprofWriter;
import shark.LeakingObjectFinder;
import shark.MetadataExtractor;
import shark.ObjectInspector;
import shark.ProguardMapping;
import shark.ProguardMappingReader;
import shark.ReferenceMatcher;
import shark.SharkLog;
import shark.ValueHolder;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;

/**
 * leakcanary-shark 2.14 consumer-side API integration test (R34).
 *
 * Exercises the core shark pipeline for real, in-process, on the OHOS device:
 *   1. Builds a small but well-formed HPROF heap dump with the public
 *      HprofWriter API (GcRoot + class dumps + two instances, A.b -> B).
 *   2. Runs the flagship HeapAnalyzer.analyze() leak analysis over that dump
 *      with retained-size computation enabled.
 *   3. Reads the same dump through Hprof.open() and looks a class up in the
 *      heap graph.
 *   4. Parses a Proguard mapping with ProguardMappingReader and deobfuscates
 *      class and field names.
 *   5. Captures a message through the SharkLog logging API.
 */
public class TestShark {
  private static int passed = 0;
  private static int failed = 0;

  // object reference field type in HPROF class dumps
  private static final int HPROF_TYPE_REFERENCE = 2;

  private static void check(boolean cond, String name) {
    if (cond) {
      System.out.println("PASS: " + name);
      passed++;
    } else {
      System.out.println("FAIL: " + name);
      failed++;
    }
  }

  private static void writeHeapDump(File hprofFile) throws Exception {
    final long stringObject = 0x100L;
    final long stringA = 0x101L;
    final long stringB = 0x102L;
    final long stringFieldB = 0x103L;
    final long classObject = 0x200L;
    final long classA = 0x201L;
    final long classB = 0x202L;
    final long instanceA = 0x301L;
    final long instanceB = 0x302L;

    HprofHeader header = new HprofHeader(
        System.currentTimeMillis(), HprofVersion.ANDROID, 4);
    HprofWriter writer = HprofWriter.Companion.openWriterFor(hprofFile, header);

    writer.write(new HprofRecord.StringRecord(stringObject, "java.lang.Object"));
    writer.write(new HprofRecord.StringRecord(stringA, "A"));
    writer.write(new HprofRecord.StringRecord(stringB, "B"));
    writer.write(new HprofRecord.StringRecord(stringFieldB, "b"));

    writer.write(new HprofRecord.LoadClassRecord(1, classObject, 0, stringObject));
    writer.write(new HprofRecord.LoadClassRecord(2, classA, 0, stringA));
    writer.write(new HprofRecord.LoadClassRecord(3, classB, 0, stringB));

    writer.write(
        new HprofRecord.HeapDumpRecord.GcRootRecord(
            // ROOT_JNI_GLOBAL is one of the root types shark indexes by
            // default (ROOT_UNKNOWN is deliberately not indexed).
            new GcRoot.JniGlobal(instanceA, 1)));

    writer.write(classDump(classObject, 0L, Collections.emptyList()));
    writer.write(classDump(classB, classObject, Collections.emptyList()));

    writer.write(classDump(
        classA,
        classObject,
        Collections.singletonList(
            new HprofRecord.HeapDumpRecord.ObjectRecord.ClassDumpRecord.FieldRecord(
                stringFieldB, HPROF_TYPE_REFERENCE))));

    byte[] aFieldValues = writer.valuesToBytes(
        Collections.singletonList((ValueHolder) new ValueHolder.ReferenceHolder(instanceB)));
    writer.write(
        new HprofRecord.HeapDumpRecord.ObjectRecord.InstanceDumpRecord(
            instanceA, 0, classA, aFieldValues));
    writer.write(
        new HprofRecord.HeapDumpRecord.ObjectRecord.InstanceDumpRecord(
            instanceB, 0, classB, new byte[0]));

    writer.close();
  }

  private static HprofRecord.HeapDumpRecord.ObjectRecord.ClassDumpRecord classDump(
      long id, long superclassId,
      java.util.List<HprofRecord.HeapDumpRecord.ObjectRecord.ClassDumpRecord.FieldRecord> fields) {
    return new HprofRecord.HeapDumpRecord.ObjectRecord.ClassDumpRecord(
        id, 0, superclassId, 0L, 0L, 0L, 0, Collections.emptyList(), fields);
  }

  private static void testHeapAnalyzerAndGraph() throws Exception {
    File hprofFile = File.createTempFile("shark-api-test", ".hprof");
    try {
      writeHeapDump(hprofFile);

      HeapAnalysis analysis = new HeapAnalyzer(step -> { }).analyze(
          hprofFile,
          (LeakingObjectFinder) graph -> Collections.singleton(0x301L),
          new ArrayList<ReferenceMatcher>(),
          true,
          new ArrayList<ObjectInspector>(),
          (MetadataExtractor) graph -> new HashMap<String, String>(),
          (ProguardMapping) null);

      check(analysis instanceof HeapAnalysisSuccess,
          "heap-analysis-success (" + analysis.getClass().getSimpleName() + ")");
      if (analysis instanceof HeapAnalysisSuccess) {
        HeapAnalysisSuccess success = (HeapAnalysisSuccess) analysis;
        check(success.getApplicationLeaks().size() == 1,
            "heap-analysis-application-leak-count ("
                + success.getApplicationLeaks().size() + ")");
        if (!success.getApplicationLeaks().isEmpty()) {
          ApplicationLeak leak = success.getApplicationLeaks().get(0);
          String trace = leak.getLeakTraces().get(0).toString();
          check(trace.contains("A"),
              "heap-analysis-leak-trace-mentions-A");
          System.out.println("---- leak trace ----\n" + trace + "--------------------");
        }
      }

      CloseableHeapGraph graph = HprofHeapGraph.Companion.openHeapGraph(
          hprofFile, (ProguardMapping) null,
          HprofIndex.Companion.defaultIndexedGcRootTags());
      try {
        check(graph.findClassByName("A") != null,
            "heap-graph-class-lookup");
        check(graph.findClassByName("B") != null,
            "heap-graph-class-lookup-B");
        check(graph.getGcRoots().size() == 1,
            "heap-graph-gc-roots (" + graph.getGcRoots().size() + ")");
      } finally {
        graph.close();
      }
    } finally {
      hprofFile.delete();
    }
  }

  private static void testProguardMapping() throws Exception {
    String mappingText =
        "A -> a:\n" +
        "  B b -> c\n";
    ProguardMapping mapping = new ProguardMappingReader(
        new ByteArrayInputStream(mappingText.getBytes("UTF-8")))
        .readProguardMapping();
    check("A".equals(mapping.deobfuscateClassName("a")),
        "proguard-mapping-deobfuscate-class");
    check("b".equals(mapping.deobfuscateFieldName("a", "c")),
        "proguard-mapping-deobfuscate-field");
  }

  private static void testSharkLog() {
    final String[] captured = new String[1];
    SharkLog.INSTANCE.setLogger(new SharkLog.Logger() {
      @Override public void d(String message) {
        captured[0] = message;
      }
      @Override public void d(Throwable throwable, String message) {
        captured[0] = message;
      }
    });
    SharkLog.INSTANCE.d(
        (kotlin.jvm.functions.Function0<String>) () -> "shark-log-test-message");
    check(captured[0] != null && captured[0].contains("shark-log-test-message"),
        "sharklog-message-captured");
  }

  public static void main(String[] args) throws Exception {
    System.out.println("=== leakcanary-shark 2.14 API integration test ===");
    testHeapAnalyzerAndGraph();
    testProguardMapping();
    testSharkLog();
    System.out.println("TOTAL passed=" + passed + " failed=" + failed);
    if (failed == 0 && passed >= 6) {
      System.out.println("PASS: all " + passed + " shark API integration tests passed");
    } else {
      System.out.println("FAIL: " + failed + " shark API integration tests failed");
      System.exit(1);
    }
  }
}
