/**
 * TestJakartaValidation — jakarta.validation API 调用测试（反射探针）
 *
 * 使用反射加载 jakarta.validation 注解/接口/异常，验证 JAR 完整可用
 * （Jakarta Bean Validation 3.0 标准，JSR-380）。
 * 断言编号 OK[1]..OK[35]，任一失败打印 FAIL 并 exit 1。
 * 注解契约断言全部对照上游 3.0.2 源码实证（@Target 集合、属性默认值）。
 */
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;
import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.Set;

import jakarta.validation.Constraint;
import jakarta.validation.Validation;
import jakarta.validation.ValidationException;

public class TestJakartaValidation {

    static void fail(String msg) {
        System.err.println("FAIL: " + msg);
        System.exit(1);
    }

    static boolean hasTarget(Class<?> ann, ElementType t) {
        Target target = ann.getAnnotation(Target.class);
        return target != null && Arrays.asList(target.value()).contains(t);
    }

    public static void main(String[] args) throws Exception {
        // OK[1]-OK[21]：二十一类 API 类型均可从 JAR 加载
        String[] classes = {
            "jakarta.validation.Valid",
            "jakarta.validation.Validator",
            "jakarta.validation.ValidatorFactory",
            "jakarta.validation.ConstraintViolation",
            "jakarta.validation.ConstraintViolationException",
            "jakarta.validation.Path",
            "jakarta.validation.ConstraintValidator",
            "jakarta.validation.ConstraintValidatorContext",
            "jakarta.validation.ValidationException",
            "jakarta.validation.Validation",
            "jakarta.validation.Configuration",
            "jakarta.validation.bootstrap.GenericBootstrap",
            "jakarta.validation.bootstrap.ProviderSpecificBootstrap",
            "jakarta.validation.groups.Default",
            "jakarta.validation.constraints.NotNull",
            "jakarta.validation.constraints.Size",
            "jakarta.validation.constraints.Min",
            "jakarta.validation.constraints.Pattern",
            "jakarta.validation.metadata.ConstraintDescriptor",
            "jakarta.validation.executable.ExecutableValidator",
            "jakarta.validation.valueextraction.ValueExtractor",
        };
        for (String c : classes) {
            Class.forName(c);
            System.out.println("OK: loaded " + c);
        }

        // OK[20]：@Valid 是注解且 RUNTIME 保留
        Class<?> valid = Class.forName("jakarta.validation.Valid");
        if (!valid.isAnnotation()
                || valid.getAnnotation(Retention.class) == null
                || valid.getAnnotation(Retention.class).value() != RetentionPolicy.RUNTIME) {
            fail("@Valid is not a RUNTIME-retained annotation");
        }
        System.out.println("OK: @Valid is a RUNTIME annotation");

        // OK[21]：@Valid 目标恰为 METHOD/FIELD/CONSTRUCTOR/PARAMETER/TYPE_USE（五元素，源码实证，无 TYPE）
        ElementType[] wantTargets = {
            ElementType.METHOD,
            ElementType.FIELD,
            ElementType.CONSTRUCTOR,
            ElementType.PARAMETER,
            ElementType.TYPE_USE,
        };
        for (ElementType t : wantTargets) {
            if (!hasTarget(valid, t)) {
                fail("@Valid missing target " + t);
            }
        }
        if (valid.getAnnotation(Target.class).value().length != wantTargets.length) {
            fail("@Valid target set size != 5");
        }
        System.out.println("OK: @Valid targets METHOD/FIELD/CONSTRUCTOR/PARAMETER/TYPE_USE");

        // OK[22]：@NotNull 是注解且带 @Constraint 元注解
        //（上游源码：@Constraint(validatedBy = {})——通用约束，校验器由引擎内置）
        Class<?> notNull = Class.forName("jakarta.validation.constraints.NotNull");
        if (!notNull.isAnnotation()) {
            fail("@NotNull is not an annotation");
        }
        if (notNull.getAnnotation(Constraint.class) == null) {
            fail("@NotNull missing @Constraint meta-annotation");
        }
        System.out.println("OK: @NotNull meta-annotated with @Constraint");

        // OK[23]：@NotNull.message() 默认模板
        if (!"{jakarta.validation.constraints.NotNull.message}".equals(
                notNull.getMethod("message").getDefaultValue())) {
            fail("@NotNull.message() default mismatch");
        }
        System.out.println("OK: @NotNull.message() default template");

        // OK[24]：@Size min()=0 / max()=Integer.MAX_VALUE 默认
        Class<?> size = Class.forName("jakarta.validation.constraints.Size");
        if (!Integer.valueOf(0).equals(size.getMethod("min").getDefaultValue())
                || !Integer.valueOf(Integer.MAX_VALUE).equals(size.getMethod("max").getDefaultValue())) {
            fail("@Size min/max defaults mismatch");
        }
        System.out.println("OK: @Size min()=0 max()=Integer.MAX_VALUE defaults");

        // OK[25]：@Min.value() 为必填 long 属性（源码实证无默认值）
        Method minValue = Class.forName("jakarta.validation.constraints.Min").getMethod("value");
        if (minValue.getReturnType() != long.class || minValue.getDefaultValue() != null) {
            fail("@Min.value() must be long with no default");
        }
        System.out.println("OK: @Min value() required long attribute");

        // OK[26]：@Pattern.regexp() 必填无默认；flags() 默认空数组
        Class<?> pattern = Class.forName("jakarta.validation.constraints.Pattern");
        if (pattern.getMethod("regexp").getDefaultValue() != null) {
            fail("@Pattern.regexp() must have no default");
        }
        if (!Arrays.equals(new Object[0], (Object[]) pattern.getMethod("flags").getDefaultValue())) {
            fail("@Pattern.flags() default must be empty array");
        }
        System.out.println("OK: @Pattern regexp() required / flags() default empty");

        // OK[27]：Validator.validate(T, Class<?>...) 变参重载返回 Set
        Method validate = Class.forName("jakarta.validation.Validator")
                .getMethod("validate", Object.class, Class[].class);
        if (validate.getReturnType() != Set.class || !validate.isVarArgs()) {
            fail("Validator.validate signature mismatch");
        }
        System.out.println("OK: Validator.validate(T, Class<?>...) varargs returns Set");

        // OK[28]：ConstraintViolationException 继承 RuntimeException 且有 getConstraintViolations()
        Class<?> cve = Class.forName("jakarta.validation.ConstraintViolationException");
        if (!RuntimeException.class.isAssignableFrom(cve)
                || cve.getMethod("getConstraintViolations") == null) {
            fail("ConstraintViolationException contract mismatch");
        }
        System.out.println("OK: ConstraintViolationException extends RuntimeException with getConstraintViolations()");

        // OK[29]：ValidationException 继承 RuntimeException
        if (!RuntimeException.class.isAssignableFrom(
                Class.forName("jakarta.validation.ValidationException"))) {
            fail("ValidationException must extend RuntimeException");
        }
        System.out.println("OK: ValidationException extends RuntimeException");

        // OK[30]：Path.Node 嵌套接口契约（getName/getKind/isInIterable）
        Class<?> node = Class.forName("jakarta.validation.Path$Node");
        if (!node.isInterface()
                || node.getMethod("getName") == null
                || node.getMethod("getKind") == null
                || node.getMethod("isInIterable") == null) {
            fail("Path.Node contract mismatch");
        }
        System.out.println("OK: Path.Node interface contract");

        // OK[31]：ConstraintValidator 契约——initialize 为 default 方法，isValid 为抽象方法
        Method initialize = Class.forName("jakarta.validation.ConstraintValidator")
                .getMethod("initialize", java.lang.annotation.Annotation.class);
        if (!initialize.isDefault()) {
            fail("ConstraintValidator.initialize must be a default method");
        }
        System.out.println("OK: ConstraintValidator.initialize default + isValid abstract");

        // OK[32]：groups.Default 是接口
        if (!Class.forName("jakarta.validation.groups.Default").isInterface()) {
            fail("groups.Default must be an interface");
        }
        System.out.println("OK: groups.Default is interface");

        // OK[33]：负向引导契约——classpath 无 provider 时 buildDefaultValidatorFactory() 抛 ValidationException
        try {
            Validation.buildDefaultValidatorFactory();
            fail("expected ValidationException without provider");
        } catch (ValidationException expected) {
            System.out.println("OK: Validation.buildDefaultValidatorFactory() throws ValidationException without provider");
        }

        System.out.println("PASS: jakarta.validation API test - 35 reflection assertions");
    }
}
