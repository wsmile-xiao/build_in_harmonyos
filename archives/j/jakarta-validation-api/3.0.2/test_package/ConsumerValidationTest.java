/**
 * ConsumerValidationTest — jakarta.validation 完整消费者用例（端到端）
 *
 * 用 jakarta.validation API 实现一个最小 Bean Validation 引擎，跑通真实校验流程：
 *   约束注解声明(@NotNull/@Size/@Min) → ConstraintValidator 注册执行 →
 *   ConstraintViolation 报告(propertyPath/invalidValue/消息模板) →
 *   ConstraintViolationException 集成。
 *
 * 与 Hibernate Validator 同构的最小引擎：注解驱动、按注解类型映射校验器工厂、
 * 违规携带完整 SPI 信息。API jar 无实现（约束注解 validatedBy 均为空集），
 * 故引擎自带校验器实现，纯 API jar + JDK 即可运行。
 *
 * 测试结构：10 个测试用例（E2E-1..E2E-10），每例独立 TEST PASS/FAIL 判定，
 * 汇总输出 E2E TEST SUMMARY，任一用例失败进程退出码为 1。
 */
import java.lang.annotation.Annotation;
import java.lang.reflect.Field;
import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;

import jakarta.validation.ConstraintValidator;
import jakarta.validation.ConstraintValidatorContext;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.ConstraintViolationException;
import jakarta.validation.ElementKind;
import jakarta.validation.Path;
import jakarta.validation.ValidationException;
import jakarta.validation.Validator;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public class ConsumerValidationTest {

    // ------------------------------------------------------------------
    // 被校验的业务对象（约束注解声明即真实消费者用法）
    // ------------------------------------------------------------------
    static class Person {
        @NotNull
        String name;
        @Size(min = 1, max = 10)
        String nickname;
        @Min(18)
        int age;

        Person(String name, String nickname, int age) {
            this.name = name;
            this.nickname = nickname;
            this.age = age;
        }
    }

    // ------------------------------------------------------------------
    // ConstraintValidator 实现（校验逻辑消费 API 的 SPI 契约）
    // ------------------------------------------------------------------
    static class NotNullValidator implements ConstraintValidator<NotNull, Object> {
        public void initialize(NotNull annotation) {
            // 通用约束：无需属性
        }

        public boolean isValid(Object value, ConstraintValidatorContext context) {
            return value != null;
        }
    }

    static class SizeValidator implements ConstraintValidator<Size, String> {
        int min;
        int max;

        public void initialize(Size annotation) {
            // 引擎初始化即消费注解属性（与真实 BV 一致）
            min = annotation.min();
            max = annotation.max();
        }

        public boolean isValid(String value, ConstraintValidatorContext context) {
            // null 值由引擎判定为合法（@Size 忽略 null，spec 语义）
            return value == null || (value.length() >= min && value.length() <= max);
        }
    }

    static class MinValidator implements ConstraintValidator<Min, Integer> {
        long min;

        public void initialize(Min annotation) {
            min = annotation.value();
        }

        public boolean isValid(Integer value, ConstraintValidatorContext context) {
            return value == null || value >= min;
        }
    }

    // ------------------------------------------------------------------
    // Path 实现（违规属性路径 SPI）
    // ------------------------------------------------------------------
    static class NodeImpl implements Path.Node {
        private final String name;

        NodeImpl(String name) {
            this.name = name;
        }

        public String getName() {
            return name;
        }

        public boolean isInIterable() {
            return false;
        }

        public Integer getIndex() {
            return null;
        }

        public Object getKey() {
            return null;
        }

        public ElementKind getKind() {
            return ElementKind.PROPERTY;
        }

        public <T extends Path.Node> T as(Class<T> nodeType) {
            return nodeType.cast(this);
        }

        @Override
        public String toString() {
            return name;
        }
    }

    static class PathImpl implements Path {
        private final String name;

        PathImpl(String name) {
            this.name = name;
        }

        public Iterator<Node> iterator() {
            return Collections.<Node>singletonList(new NodeImpl(name)).iterator();
        }

        @Override
        public String toString() {
            return name;
        }
    }

    // ------------------------------------------------------------------
    // ConstraintViolation 实现（违规报告 SPI，覆盖全部抽象方法）
    // ------------------------------------------------------------------
    static class Violation<T> implements ConstraintViolation<T> {
        private final T rootBean;
        private final String message;
        private final Object invalidValue;
        private final Path path;

        Violation(T rootBean, String message, Object invalidValue, Path path) {
            this.rootBean = rootBean;
            this.message = message;
            this.invalidValue = invalidValue;
            this.path = path;
        }

        public String getMessage() {
            return message;
        }

        public String getMessageTemplate() {
            return message;
        }

        public T getRootBean() {
            return rootBean;
        }

        @SuppressWarnings("unchecked")
        public Class<T> getRootBeanClass() {
            return (Class<T>) rootBean.getClass();
        }

        public Object getLeafBean() {
            return rootBean;
        }

        public Object[] getExecutableParameters() {
            return new Object[0];
        }

        public Object getExecutableReturnValue() {
            return null;
        }

        public Path getPropertyPath() {
            return path;
        }

        public Object getInvalidValue() {
            return invalidValue;
        }

        public jakarta.validation.metadata.ConstraintDescriptor<?> getConstraintDescriptor() {
            // 最小引擎不构建描述符（本用例不断言此项）
            return null;
        }

        public <U> U unwrap(Class<U> type) {
            throw new ValidationException("Not unwrappable to " + type);
        }
    }

    // ------------------------------------------------------------------
    // 最小引擎：Validator 接口实现（注解类型 → 校验器工厂映射）
    // ------------------------------------------------------------------
    static class MiniValidator implements Validator {
        /** 注解类型 → 校验器实现类（工厂注册表，与真实 BV 的约束映射同构） */
        final Map<Class<? extends Annotation>, Class<? extends ConstraintValidator<?, ?>>> factories =
                new HashMap<Class<? extends Annotation>, Class<? extends ConstraintValidator<?, ?>>>();

        MiniValidator() {
            factories.put(NotNull.class, NotNullValidator.class);
            factories.put(Size.class, SizeValidator.class);
            factories.put(Min.class, MinValidator.class);
        }

        /** 按注解声明创建校验器实例并 initialize（每字段每注解独立实例，真实 BV 语义） */
        ConstraintValidator<?, ?> createValidator(Annotation a) {
            Class<? extends ConstraintValidator<?, ?>> factory = factories.get(a.annotationType());
            if (factory == null) {
                return null;
            }
            try {
                ConstraintValidator<?, ?> v = factory.getDeclaredConstructor().newInstance();
                ((ConstraintValidator) v).initialize(a);
                return v;
            } catch (ReflectiveOperationException e) {
                throw new IllegalStateException(e);
            }
        }

        public <T> Set<ConstraintViolation<T>> validate(T object, Class<?>... groups) {
            Set<ConstraintViolation<T>> violations = new LinkedHashSet<ConstraintViolation<T>>();
            for (Field f : object.getClass().getDeclaredFields()) {
                f.setAccessible(true);
                for (Annotation a : f.getDeclaredAnnotations()) {
                    ConstraintValidator validator = createValidator(a);
                    if (validator == null) {
                        continue;
                    }
                    Object value;
                    try {
                        value = f.get(object);
                    } catch (IllegalAccessException e) {
                        throw new IllegalStateException(e);
                    }
                    @SuppressWarnings("unchecked")
                    boolean ok = ((ConstraintValidator) validator).isValid(value, null);
                    if (!ok) {
                        violations.add(new Violation<T>(object, messageOf(a), value,
                                new PathImpl(f.getName())));
                    }
                }
            }
            return violations;
        }

        /** 读取注解实例的 message() 实际值（未覆写时即默认模板） */
        private static String messageOf(Annotation a) {
            try {
                return String.valueOf(a.annotationType().getMethod("message").invoke(a));
            } catch (Exception e) {
                return "invalid";
            }
        }

        // 以下为 Validator 接口其余方法（本用例不使用的完整实现契约）：
        public <T> Set<ConstraintViolation<T>> validateProperty(T object, String propertyName,
                                                                Class<?>... groups) {
            throw new UnsupportedOperationException("validateProperty not used in this test");
        }

        public <T> Set<ConstraintViolation<T>> validateValue(Class<T> beanType, String propertyName,
                                                             Object value, Class<?>... groups) {
            throw new UnsupportedOperationException("validateValue not used in this test");
        }

        public jakarta.validation.metadata.BeanDescriptor getConstraintsForClass(Class<?> clazz) {
            throw new UnsupportedOperationException("getConstraintsForClass not used in this test");
        }

        public <T> T unwrap(Class<T> type) {
            if (type.isAssignableFrom(getClass())) {
                return type.cast(this);
            }
            throw new ValidationException("Not unwrappable to " + type);
        }

        public jakarta.validation.executable.ExecutableValidator forExecutables() {
            throw new UnsupportedOperationException("forExecutables not used in this test");
        }
    }

    // ------------------------------------------------------------------
    // 测试执行器（每例独立 TEST PASS/FAIL，汇总 SUMMARY，任一失败 exit 1）
    // ------------------------------------------------------------------
    static int passed = 0;
    static int failed = 0;

    static void runCase(String name, boolean ok, String failReason) {
        if (ok) {
            passed++;
            System.out.println("TEST PASS: " + name);
        } else {
            failed++;
            System.out.println("TEST FAIL: " + name + " - " + failReason);
        }
    }

    static String defaultMessage(Class<? extends Annotation> ann) {
        try {
            return String.valueOf(ann.getMethod("message").getDefaultValue());
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    public static void main(String[] args) throws Exception {
        MiniValidator engine = new MiniValidator();

        // E2E-1：合法对象零违规
        runCase("E2E-1 合法对象零违规",
                engine.validate(new Person("alice", "ali", 20)).isEmpty(),
                "validate(valid bean) must return empty set");

        // E2E-2：@NotNull 违规报告契约（propertyPath/invalidValue/消息模板/rootBean）
        Person p2 = new Person(null, "ali", 20);
        Set<ConstraintViolation<Person>> v2 = engine.validate(p2);
        boolean e2 = v2.size() == 1;
        if (e2) {
            ConstraintViolation<Person> cv = v2.iterator().next();
            e2 = "name".equals(cv.getPropertyPath().toString())
                    && cv.getInvalidValue() == null
                    && defaultMessage(NotNull.class).equals(cv.getMessage())
                    && cv.getRootBean() == p2
                    && cv.getRootBeanClass() == Person.class;
        }
        runCase("E2E-2 @NotNull 违规报告契约(path/invalidValue/消息模板/rootBean)",
                e2, "violation contract mismatch");

        // E2E-3：@Size 长度契约三态（0 字符违规 / 11 字符违规 / 10 字符边界通过）
        boolean e3 = engine.validate(new Person("a", "", 20)).size() == 1;
        e3 &= engine.validate(new Person("a", "0123456789A", 20)).size() == 1;
        e3 &= engine.validate(new Person("a", "0123456789", 20)).isEmpty();
        runCase("E2E-3 @Size 长度契约三态(0字符/11字符违规,10字符边界通过)",
                e3, "@Size range contract mismatch");

        // E2E-4：@Min 边界契约（17 违规 / 18 边界通过）
        boolean e4 = false;
        Set<ConstraintViolation<Person>> v4 = engine.validate(new Person("a", "b", 17));
        if (v4.size() == 1) {
            ConstraintViolation<Person> cv = v4.iterator().next();
            e4 = "age".equals(cv.getPropertyPath().toString())
                    && Integer.valueOf(17).equals(cv.getInvalidValue())
                    && defaultMessage(Min.class).equals(cv.getMessage());
        }
        e4 &= engine.validate(new Person("a", "b", 18)).isEmpty();
        runCase("E2E-4 @Min 边界契约(17违规/18边界通过)", e4, "@Min boundary contract mismatch");

        // E2E-5：多字段同时违规不短路（name+nickname+age 恰 3 条）
        Set<ConstraintViolation<Person>> v5 = engine.validate(new Person(null, "", 17));
        runCase("E2E-5 多字段同时违规不短路(恰 3 条)",
                v5.size() == 3, "expected exactly 3 violations");

        // E2E-6：引擎无跨对象状态残留
        boolean e6 = engine.validate(new Person(null, "", 17)).size() == 3
                && engine.validate(new Person("bob", "b", 18)).isEmpty();
        runCase("E2E-6 引擎无跨对象状态残留", e6, "engine state leaked across validates");

        // E2E-7：ConstraintViolationException 集成（上游源码实证：构造函数防御性拷贝
        // new HashSet<>(constraintViolations)，断言拷贝后包含同一批违规元素）
        Set<ConstraintViolation<Person>> v7 = engine.validate(new Person(null, "x", 1));
        ConstraintViolationException ex = new ConstraintViolationException(v7);
        Set<ConstraintViolation<?>> reported = ex.getConstraintViolations();
        boolean e7 = ex instanceof RuntimeException
                && reported != null
                && reported.size() == v7.size()
                && reported.containsAll(v7);
        runCase("E2E-7 ConstraintViolationException 集成(防御性拷贝同一违规集)",
                e7, "exception integration mismatch");

        // E2E-8：注解属性与引擎消费一致（groups/payload 空数组、Size 1-10、Min 18）
        NotNull nn = Person.class.getDeclaredField("name").getAnnotation(NotNull.class);
        boolean e8 = nn.groups().length == 0 && nn.payload().length == 0;
        Size sz = Person.class.getDeclaredField("nickname").getAnnotation(Size.class);
        e8 &= sz.min() == 1 && sz.max() == 10;
        Min mn = Person.class.getDeclaredField("age").getAnnotation(Min.class);
        e8 &= mn.value() == 18;
        runCase("E2E-8 注解属性与引擎消费一致(groups/payload空,Size 1-10,Min 18)",
                e8, "annotation attribute mismatch");

        // E2E-9：校验器工厂映射与校验逻辑（initialize 消费注解属性，@NotNull/@Size 真实判定）
        ConstraintValidator<?, ?> notNullVal = engine.createValidator(
                Person.class.getDeclaredField("name").getAnnotation(NotNull.class));
        ConstraintValidator<?, ?> sizeVal = engine.createValidator(
                Person.class.getDeclaredField("nickname").getAnnotation(Size.class));
        boolean e9 = notNullVal != null && sizeVal != null
                && ((NotNullValidator) notNullVal).isValid("x", null)
                && !((NotNullValidator) notNullVal).isValid(null, null)
                && ((SizeValidator) sizeVal).min == 1
                && ((SizeValidator) sizeVal).max == 10;
        runCase("E2E-9 校验器工厂映射与校验逻辑(initialize 消费注解属性)",
                e9, "validator factory mapping mismatch");

        // E2E-10：Validator 接口契约（instanceof + unwrap 不支持类型抛 ValidationException）
        boolean e10 = engine instanceof Validator;
        try {
            engine.unwrap(String.class);
            e10 = false;
        } catch (ValidationException expected) {
            // unwrap 到不支持的运行时类型必须抛 ValidationException（spec 语义）
        }
        runCase("E2E-10 Validator 接口契约(instanceof+unwrap 抛 ValidationException)",
                e10, "Validator contract mismatch");

        System.out.println("E2E TEST SUMMARY: " + passed + " passed, " + failed + " failed");
        if (failed > 0) {
            System.exit(1);
        }
        System.out.println("PASS: jakarta.validation consumer E2E - mini Bean Validation engine");
    }
}
