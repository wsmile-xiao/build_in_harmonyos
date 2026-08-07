import com.fasterxml.jackson.core.JsonFactory;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonToken;

/**
 * TestJacksonCore — jackson-core API 调用测试
 *
 * 使用 JsonFactory/JsonParser 流式 API 解析 JSON 字符串，
 * 验证 jackson-core 库的核心功能正常工作。
 */
public class TestJacksonCore {
    public static void main(String[] args) throws Exception {
        JsonFactory factory = new JsonFactory();
        JsonParser parser = factory.createParser("{\"name\":\"test\",\"value\":42}");

        // 断言 1: 解析到 START_OBJECT
        if (parser.nextToken() != JsonToken.START_OBJECT) {
            System.err.println("FAIL: Expected START_OBJECT");
            System.exit(1);
        }

        // 断言 2: 解析到字段名 "name"
        if (parser.nextToken() != JsonToken.FIELD_NAME
                || !"name".equals(parser.getCurrentName())) {
            System.err.println("FAIL: Expected field 'name'");
            System.exit(1);
        }

        // 断言 3: 解析到字符串值 "test"
        if (parser.nextToken() != JsonToken.VALUE_STRING
                || !"test".equals(parser.getText())) {
            System.err.println("FAIL: Expected value 'test'");
            System.exit(1);
        }

        // 断言 4: 解析到字段名 "value"
        if (parser.nextToken() != JsonToken.FIELD_NAME
                || !"value".equals(parser.getCurrentName())) {
            System.err.println("FAIL: Expected field 'value'");
            System.exit(1);
        }

        // 断言 5: 解析到数值 42
        if (parser.nextToken() != JsonToken.VALUE_NUMBER_INT
                || parser.getIntValue() != 42) {
            System.err.println("FAIL: Expected value 42");
            System.exit(1);
        }

        // 断言 6: 解析到 END_OBJECT
        if (parser.nextToken() != JsonToken.END_OBJECT) {
            System.err.println("FAIL: Expected END_OBJECT");
            System.exit(1);
        }

        System.out.println("PASS: jackson-core API test - JSON parsing works correctly");
        parser.close();
    }
}
