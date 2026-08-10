import io.airlift.slice.Slice;
import io.airlift.slice.Slices;

/**
 * TestAirliftSlice — airlift-slice 0.16 API 调用测试
 *
 * 使用 Slices.wrappedBuffer / Slice.getByte / getBytes / length 等 API，
 * 验证 airlift-slice 库的核心功能正常工作。
 */
public class TestAirliftSlice {
    public static void main(String[] args) throws Exception {
        // 断言 1: 用 wrappedBuffer 包装字节数组，length 应为 5
        Slice slice = Slices.wrappedBuffer(new byte[]{1, 2, 3, 4, 5});
        if (slice.length() != 5) {
            System.err.println("FAIL: Expected length 5, got " + slice.length());
            System.exit(1);
        }

        // 断言 2: getByte(0) 应为 1
        if (slice.getByte(0) != 1) {
            System.err.println("FAIL: Expected byte 1 at index 0");
            System.exit(1);
        }

        // 断言 3: getByte(4) 应为 5
        if (slice.getByte(4) != 5) {
            System.err.println("FAIL: Expected byte 5 at index 4");
            System.exit(1);
        }

        // 断言 4: getBytes() 应返回 5 字节原数组
        byte[] all = slice.getBytes();
        if (all.length != 5 || all[0] != 1 || all[4] != 5) {
            System.err.println("FAIL: getBytes() returned wrong data");
            System.exit(1);
        }

        // 断言 5: getBytes(1, 3) 应返回 [2, 3, 4]
        byte[] sub = slice.getBytes(1, 3);
        if (sub.length != 3 || sub[0] != 2 || sub[2] != 4) {
            System.err.println("FAIL: getBytes(1, 3) returned wrong data");
            System.exit(1);
        }

        // 断言 6: EMPTY_SLICE 长度应为 0
        if (Slices.EMPTY_SLICE.length() != 0) {
            System.err.println("FAIL: EMPTY_SLICE length != 0");
            System.exit(1);
        }

        System.out.println("PASS: airlift-slice API test - Slice/Slices work correctly");
    }
}
