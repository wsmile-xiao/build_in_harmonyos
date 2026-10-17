/**
 * TestJakartaCdi — jakarta.enterprise.cdi-api + lang-model API 调用测试
 *
 * 使用反射加载并断言 jakarta.enterprise 命名空间的核心类型，
 * 验证两个 JAR（cdi-api + lang-model）中的 API 完整可用（CDI 4.0 标准）。
 * 仅使用 JDK 类型（Class.forName + java.lang.reflect），编译期不依赖被测 JAR。
 */
public class TestJakartaCdi {

    private static int passed = 0;

    private static void ok(String msg) {
        passed++;
        System.out.println("OK[" + passed + "]: " + msg);
    }

    private static void fail(String msg) {
        System.err.println("FAIL: " + msg);
        System.exit(1);
    }

    private static Class<?> load(String name) throws Exception {
        Class<?> c = Class.forName(name);
        ok("loaded " + name);
        return c;
    }

    public static void main(String[] args) throws Exception {
        // 断言 1-11：两个 JAR 的核心类型均可加载（cdi-api 7 个 + lang-model 4 个）
        Class<?> requestScoped = load("jakarta.enterprise.context.RequestScoped");
        Class<?> applicationScoped = load("jakarta.enterprise.context.ApplicationScoped");
        Class<?> sessionScoped = load("jakarta.enterprise.context.SessionScoped");
        load("jakarta.enterprise.context.Dependent");
        Class<?> normalScope = load("jakarta.enterprise.context.NormalScope");
        Class<?> event = load("jakarta.enterprise.event.Event");
        Class<?> annotationLiteral = load("jakarta.enterprise.util.AnnotationLiteral");
        load("jakarta.enterprise.lang.model.AnnotationInfo");
        load("jakarta.enterprise.lang.model.declarations.ClassInfo");
        Class<?> langType = load("jakarta.enterprise.lang.model.types.Type");
        Class<?> annotationTarget = load("jakarta.enterprise.lang.model.AnnotationTarget");

        // 断言 12：作用域注解本身是注解类型（可标注 bean 类/方法/字段）
        if (!requestScoped.isAnnotation()) {
            fail("RequestScoped is not an annotation type");
        }
        ok("RequestScoped is an annotation type");

        // 断言 13-15：三个作用域注解携带 @NormalScope 元注解（CDI 自定义作用域契约）
        Class<? extends java.lang.annotation.Annotation> nsMeta =
                normalScope.asSubclass(java.lang.annotation.Annotation.class);
        if (!requestScoped.isAnnotationPresent(nsMeta)) {
            fail("RequestScoped missing @NormalScope meta-annotation");
        }
        ok("RequestScoped carries @NormalScope");
        if (!applicationScoped.isAnnotationPresent(nsMeta)) {
            fail("ApplicationScoped missing @NormalScope meta-annotation");
        }
        ok("ApplicationScoped carries @NormalScope");
        java.lang.annotation.Annotation sessionAnno = sessionScoped.getAnnotation(nsMeta);
        if (sessionAnno == null) {
            fail("SessionScoped missing @NormalScope meta-annotation");
        }
        Object passivating = normalScope.getMethod("passivating").invoke(sessionAnno);
        if (!Boolean.TRUE.equals(passivating)) {
            fail("SessionScoped @NormalScope(passivating=true) expected");
        }
        ok("SessionScoped carries @NormalScope(passivating=true)");

        // 断言 16：@NormalScope 只允许标注注解类型（元注解约束）
        java.lang.annotation.Target target =
                normalScope.getAnnotation(java.lang.annotation.Target.class);
        if (target == null) {
            fail("@NormalScope missing @Target");
        }
        java.lang.annotation.ElementType[] targetValues = target.value();
        if (targetValues.length != 1
                || targetValues[0] != java.lang.annotation.ElementType.ANNOTATION_TYPE) {
            fail("@NormalScope @Target must be exactly ANNOTATION_TYPE");
        }
        ok("@NormalScope declares @Target(ANNOTATION_TYPE)");

        // 断言 17：Event 提供 3 个 select 重载（程序化事件触发契约）
        int selectCount = 0;
        for (java.lang.reflect.Method m : event.getMethods()) {
            if (m.getName().equals("select")) {
                selectCount++;
            }
        }
        if (selectCount != 3) {
            fail("Event.select overloads expected 3, found " + selectCount);
        }
        ok("Event has 3 select() overloads");

        // 断言 18：AnnotationLiteral 实现 java.lang.annotation.Annotation（类型安全限定符基类）
        if (!java.lang.annotation.Annotation.class.isAssignableFrom(annotationLiteral)) {
            fail("AnnotationLiteral does not implement java.lang.annotation.Annotation");
        }
        ok("AnnotationLiteral implements java.lang.annotation.Annotation");

        // 断言 19：lang-model 的类型体系是接口且有继承关系（Lang Model 4.0 契约）
        if (!langType.isInterface()
                || !annotationTarget.isAssignableFrom(langType)) {
            fail("lang.model.types.Type must be an interface extending AnnotationTarget");
        }
        ok("lang.model.types.Type is an interface extending AnnotationTarget");

        System.out.println("PASS: jakarta.cdi API test - " + passed
                + " reflection assertions passed (cdi-api + lang-model jars)");
    }
}
