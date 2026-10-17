/**
 * TestJakartaInject — jakarta.inject API 调用测试
 *
 * 使用反射加载 jakarta.inject 注解与接口，
 * 验证 JAR 中的 API 完整可用（JSR-330 依赖注入标准）。
 */
public class TestJakartaInject {
    public static void main(String[] args) throws Exception {
        String[] classes = {
            "jakarta.inject.Inject",
            "jakarta.inject.Named",
            "jakarta.inject.Provider",
            "jakarta.inject.Qualifier",
            "jakarta.inject.Scope",
            "jakarta.inject.Singleton",
        };

        // 断言 1-6: 六类注解/接口均可从 JAR 加载
        for (String c : classes) {
            Class.forName(c);
            System.out.println("OK: loaded " + c);
        }

        // 断言 7: @Inject 是注解类型（可注解构造函数/方法/字段）
        Class<?> inject = Class.forName("jakarta.inject.Inject");
        if (!inject.isAnnotation()) {
            System.err.println("FAIL: Inject is not an annotation");
            System.exit(1);
        }

        // 断言 8: Provider.get() 返回 Object（DI 提供者契约）
        if (Class.forName("jakarta.inject.Provider")
                .getDeclaredMethod("get").getReturnType() != Object.class) {
            System.err.println("FAIL: Provider.get() must return Object");
            System.exit(1);
        }

        System.out.println("PASS: jakarta.inject API test - annotations/interfaces load correctly");
    }
}
