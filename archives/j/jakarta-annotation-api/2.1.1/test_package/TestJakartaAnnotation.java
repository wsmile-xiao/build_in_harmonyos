import java.lang.annotation.Documented;
import java.lang.annotation.Repeatable;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;
import java.lang.annotation.ElementType;
import jakarta.annotation.Generated;
import jakarta.annotation.ManagedBean;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import jakarta.annotation.Priority;
import jakarta.annotation.Resource;
import jakarta.annotation.Resources;
import jakarta.annotation.security.DeclareRoles;
import jakarta.annotation.security.DenyAll;
import jakarta.annotation.security.PermitAll;
import jakarta.annotation.security.RolesAllowed;
import jakarta.annotation.security.RunAs;
import jakarta.annotation.sql.DataSourceDefinition;
import jakarta.annotation.sql.DataSourceDefinitions;

/**
 * TestJakartaAnnotation — jakarta.annotation API 反射探针
 *
 * 验证 2.1.1 JAR 中全部 16 个公开注解类型可加载、注解元数据
 * （Retention/Target/Repeatable/Deprecated/Documented）与 Jakarta
 * Annotations 2.1 规范一致，防 JAR 缺类或元数据漂移。
 *
 * 类型清单来源：api/src/main/java/jakarta/annotation（19 个 .java 源文件，
 * 其中 Resource/DataSourceDefinition 各含一个嵌套/配套枚举与容器注解）。
 */
public class TestJakartaAnnotation {

    static int checks = 0;

    static void check(boolean cond, String label) {
        if (!cond) {
            System.err.println("FAIL: " + label);
            System.exit(1);
        }
        checks++;
        System.out.println("OK: " + label);
    }

    public static void main(String[] args) throws Exception {
        // ==== A. 16 个公开注解类型可从 JAR 加载（+ 1 个嵌套枚举） ====
        Class<?>[] types = {
            Generated.class, ManagedBean.class, PostConstruct.class,
            PreDestroy.class, Priority.class, Resource.class, Resources.class,
            DeclareRoles.class, DenyAll.class, PermitAll.class,
            RolesAllowed.class, RunAs.class,
            DataSourceDefinition.class, DataSourceDefinitions.class,
        };
        check(types.length == 14, "top-level annotation types count = 14");
        for (Class<?> c : types) {
            check(c.isAnnotation(),
                    "loaded annotation type " + c.getName());
        }
        // jakarta.annotation 包下另有 Nonnull/Nullable
        check(jakarta.annotation.Nonnull.class.isAnnotation(), "loaded Nonnull");
        check(jakarta.annotation.Nullable.class.isAnnotation(), "loaded Nullable");
        // 嵌套枚举 AuthenticationType
        check(Resource.AuthenticationType.class.isEnum(),
                "Resource.AuthenticationType is an enum");

        // ==== B. 方法签名/返回类型契约 ====
        check(Resource.class.getDeclaredMethod("name").getReturnType() == String.class,
                "Resource.name() returns String");
        check(Resource.class.getDeclaredMethod("lookup").getReturnType() == String.class,
                "Resource.lookup() returns String");
        check(Resource.class.getDeclaredMethod("type").getReturnType() == Class.class,
                "Resource.type() returns Class<?>");
        check(Priority.class.getDeclaredMethod("value").getReturnType() == int.class,
                "Priority.value() returns int");
        check(Generated.class.getDeclaredMethod("value").getReturnType() == String[].class,
                "Generated.value() returns String[]");
        check(RolesAllowed.class.getDeclaredMethod("value").getReturnType() == String[].class,
                "RolesAllowed.value() returns String[]");

        // ==== C. 注解元数据断言（规范定义的 Retention/Target） ====
        check(PostConstruct.class.isAnnotationPresent(Documented.class),
                "@PostConstruct is @Documented");
        check(java.util.Arrays.equals(PostConstruct.class.getAnnotation(Target.class).value(),
                new ElementType[]{ElementType.METHOD}),
                "@PostConstruct target = METHOD only");
        check(PostConstruct.class.getAnnotation(Retention.class).value() == RetentionPolicy.RUNTIME,
                "@PostConstruct retention = RUNTIME");

        check(PreDestroy.class.isAnnotationPresent(Documented.class),
                "@PreDestroy is @Documented");
        check(java.util.Arrays.equals(PreDestroy.class.getAnnotation(Target.class).value(),
                new ElementType[]{ElementType.METHOD}),
                "@PreDestroy target = METHOD only");
        check(PreDestroy.class.getAnnotation(Retention.class).value() == RetentionPolicy.RUNTIME,
                "@PreDestroy retention = RUNTIME");

        check(Resource.class.getAnnotation(Retention.class).value() == RetentionPolicy.RUNTIME,
                "@Resource retention = RUNTIME");
        check(Resource.class.getAnnotation(Repeatable.class).value() == Resources.class,
                "@Resource is @Repeatable(Resources.class)");
        check(java.util.Arrays.asList(Resource.class.getAnnotation(Target.class).value())
                .containsAll(java.util.Arrays.asList(
                        ElementType.TYPE, ElementType.FIELD, ElementType.METHOD)),
                "@Resource targets = {TYPE, FIELD, METHOD}");

        check(Generated.class.getAnnotation(Retention.class).value() == RetentionPolicy.SOURCE,
                "@Generated retention = SOURCE");
        check(Generated.class.isAnnotationPresent(Documented.class),
                "@Generated is @Documented");

        check(Priority.class.getAnnotation(Retention.class).value() == RetentionPolicy.RUNTIME,
                "@Priority retention = RUNTIME");
        check(Priority.class.isAnnotationPresent(Documented.class),
                "@Priority is @Documented");

        check(ManagedBean.class.isAnnotationPresent(Deprecated.class),
                "@ManagedBean is @Deprecated (since 2.1.1)");
        check(ManagedBean.class.getAnnotation(Retention.class).value() == RetentionPolicy.RUNTIME,
                "@ManagedBean retention = RUNTIME");

        check(RolesAllowed.class.getAnnotation(Retention.class).value() == RetentionPolicy.RUNTIME,
                "@RolesAllowed retention = RUNTIME");
        check(java.util.Arrays.equals(RolesAllowed.class.getAnnotation(Target.class).value(),
                new ElementType[]{ElementType.TYPE, ElementType.METHOD}),
                "@RolesAllowed targets = {TYPE, METHOD}");

        check(RunAs.class.getAnnotation(Retention.class).value() == RetentionPolicy.RUNTIME,
                "@RunAs retention = RUNTIME");
        check(java.util.Arrays.equals(RunAs.class.getAnnotation(Target.class).value(),
                new ElementType[]{ElementType.TYPE}),
                "@RunAs target = TYPE only");

        check(DataSourceDefinition.class.isAnnotationPresent(Repeatable.class)
                && DataSourceDefinition.class.getAnnotation(Repeatable.class).value()
                        == DataSourceDefinitions.class,
                "@DataSourceDefinition is @Repeatable(DataSourceDefinitions.class)");

        // ==== D. 成员默认值契约（Jakarta Annotations 2.1 规范） ====
        check(Resource.class.getDeclaredMethod("type").getDefaultValue() == Object.class,
                "Resource.type() default = Object.class");
        check(Boolean.TRUE.equals(Resource.class.getDeclaredMethod("shareable").getDefaultValue()),
                "Resource.shareable() default = true");
        check(Resource.class.getDeclaredMethod("authenticationType").getDefaultValue()
                == Resource.AuthenticationType.CONTAINER,
                "Resource.authenticationType() default = CONTAINER");
        check(Resource.AuthenticationType.values().length == 2,
                "Resource.AuthenticationType has exactly 2 constants");
        check(Resource.AuthenticationType.valueOf("CONTAINER") != null
                && Resource.AuthenticationType.valueOf("APPLICATION") != null,
                "AuthenticationType constants = {CONTAINER, APPLICATION}");
        check("".equals(Resource.class.getDeclaredMethod("lookup").getDefaultValue()),
                "Resource.lookup() default = \"\" (since 1.1)");
        check("".equals(Resource.class.getDeclaredMethod("mappedName").getDefaultValue()),
                "Resource.mappedName() default = \"\"");
        check("".equals(Resource.class.getDeclaredMethod("description").getDefaultValue()),
                "Resource.description() default = \"\"");
        check("".equals(Generated.class.getDeclaredMethod("date").getDefaultValue()),
                "Generated.date() default = \"\"");

        System.out.println("PASS: jakarta.annotation probe - " + checks + " assertions");
    }
}
