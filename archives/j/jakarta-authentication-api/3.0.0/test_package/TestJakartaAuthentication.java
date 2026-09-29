/**
 * TestJakartaAuthentication — jakarta.security.auth.message API 调用测试
 *
 * 使用反射加载 jakarta.security.auth.message 包内核心接口与类，
 * 验证 JAR 中的认证 SPI API 完整可用（Jakarta Authentication 3.0）。
 */
public class TestJakartaAuthentication {
    public static void main(String[] args) throws Exception {
        String[] classes = {
            "jakarta.security.auth.message.config.ServerAuthContext",
            "jakarta.security.auth.message.module.ServerAuthModule",
            "jakarta.security.auth.message.config.AuthConfigProvider",
            "jakarta.security.auth.message.config.ClientAuthContext",
            "jakarta.security.auth.message.AuthStatus",
            "jakarta.security.auth.message.MessageInfo",
            "jakarta.security.auth.message.MessagePolicy",
            "jakarta.security.auth.message.callback.CallerPrincipalCallback",
        };

        // 断言 1-8: 八类接口/类均可从 JAR 加载
        for (String c : classes) {
            Class.forName(c);
            System.out.println("OK: loaded " + c);
        }

        // 断言 9: ServerAuthModule 是接口（认证模块 SPI 契约）
        Class<?> module = Class.forName("jakarta.security.auth.message.module.ServerAuthModule");
        if (!module.isInterface()) {
            System.err.println("FAIL: ServerAuthModule is not an interface");
            System.exit(1);
        }

        // 断言 10: AuthStatus.SUCCESS 为 AuthStatus 类型常量（认证状态机契约）
        Class<?> status = Class.forName("jakarta.security.auth.message.AuthStatus");
        if (status.getField("SUCCESS").getType() != status) {
            System.err.println("FAIL: AuthStatus.SUCCESS must be of type AuthStatus");
            System.exit(1);
        }

        System.out.println("PASS: jakarta.security.auth.message API test - interfaces/classes load correctly");
    }
}
