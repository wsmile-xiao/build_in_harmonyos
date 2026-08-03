import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.jr.ob.JSON;
import com.fasterxml.jackson.jr.stree.JrSimpleTreeExtension;
import com.fasterxml.jackson.jr.stree.JrsObject;

public final class TestJacksonJr {
    public static final class Person {
        private String name;
        private int age;

        public Person() {
        }

        public Person(String name, int age) {
            this.name = name;
            this.age = age;
        }

        public String getName() {
            return name;
        }

        public void setName(String name) {
            this.name = name;
        }

        public int getAge() {
            return age;
        }

        public void setAge(int age) {
            this.age = age;
        }
    }

    private static int checks;

    private static void check(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
        checks++;
    }

    public static void main(String[] args) throws Exception {
        Map<String, Object> parsed =
                JSON.std.mapFrom(
                        "{\"id\":7,\"items\":[\"alpha\",2],\"active\":true}");
        check(parsed.size() == 3, "map size");
        check(Integer.valueOf(7).equals(parsed.get("id")), "integer value");
        check(parsed.get("items") instanceof List, "nested list type");
        check(((List<?>) parsed.get("items")).size() == 2, "nested list size");
        check(Boolean.TRUE.equals(parsed.get("active")), "boolean value");

        Person ada = JSON.std.beanFrom(
                Person.class, "{\"name\":\"Ada\",\"age\":36}");
        check("Ada".equals(ada.getName()), "bean name");
        check(ada.getAge() == 36, "bean age");

        Map<String, Object> beanRoundTrip =
                JSON.std.mapFrom(JSON.std.asString(new Person("Lin", 28)));
        check("Lin".equals(beanRoundTrip.get("name")), "serialized bean name");
        check(Integer.valueOf(28).equals(beanRoundTrip.get("age")),
                "serialized bean age");

        List<Person> people = JSON.std.listOfFrom(
                Person.class,
                "[{\"name\":\"A\",\"age\":1},{\"name\":\"B\",\"age\":2}]");
        check(people.size() == 2, "typed list size");
        check("A".equals(people.get(0).getName()), "typed list first name");
        check(people.get(1).getAge() == 2, "typed list second age");

        Map<String, Object> withNull = new LinkedHashMap<>();
        withNull.put("a", 1);
        withNull.put("b", null);
        check("{\"a\":1}".equals(JSON.std.asString(withNull)),
                "default null omission");
        check(
                "{\"a\":1,\"b\":null}".equals(
                        JSON.std
                                .with(JSON.Feature.WRITE_NULL_PROPERTIES)
                                .asString(withNull)),
                "explicit null output");

        String composed =
                JSON.std.composeString()
                        .startObject()
                        .put("answer", 42)
                        .startArrayField("flags")
                        .add(true)
                        .add(false)
                        .end()
                        .end()
                        .finish();
        check(
                "{\"answer\":42,\"flags\":[true,false]}".equals(composed),
                "composer output");

        byte[] encoded = JSON.std.asBytes(Arrays.asList("x", 3, true));
        check(
                "[\"x\",3,true]".equals(
                        new String(encoded, StandardCharsets.UTF_8)),
                "UTF-8 byte output");

        Object[] values = JSON.std.arrayFrom("[1,2,3]");
        check(values.length == 3, "JSON array length");
        check(
                Integer.valueOf(1).equals(values[0])
                        && Integer.valueOf(3).equals(values[2]),
                "JSON array values");
        check(
                new BigDecimal("10.25").equals(
                        JSON.std.beanFrom(BigDecimal.class, "10.25")),
                "BigDecimal value");

        JSON treeJson =
                JSON.builder().register(new JrSimpleTreeExtension()).build();
        JrsObject tree =
                (JrsObject) treeJson.treeFrom(
                        "{\"name\":\"tree\",\"active\":true}");
        check(tree instanceof JrsObject, "tree object type");
        check(tree.size() == 2, "tree size");
        check("tree".equals(tree.get("name").asText()), "tree text value");
        check("true".equals(tree.get("active").asText()), "tree boolean value");
        check(
                "{\"name\":\"tree\",\"active\":true}".equals(
                        treeJson.asString(tree)),
                "tree round trip");

        boolean invalidRejected = false;
        try {
            JSON.std.anyFrom("{");
        } catch (Exception expected) {
            invalidRejected = true;
        }
        check(invalidRejected, "invalid JSON must be rejected");

        if (checks != 25) {
            throw new AssertionError(
                    "consumer assertion count: " + checks + " (expected 25)");
        }
        System.out.println(
                "jackson-jr 2.14.0 consumer tests passed: " + checks);
    }
}
