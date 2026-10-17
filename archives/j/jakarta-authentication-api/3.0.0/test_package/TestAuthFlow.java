/**
 * TestAuthFlow — jakarta.security.auth.message 认证 SPI 完整消费者测试（端到端）
 *
 * 模拟一个服务器容器：容器提供并安装 AuthConfigFactory 实现，注册认证配置提供者，
 * 通过工厂取回提供者，取得 ServerAuthConfig/ServerAuthContext，跑通一次完整的
 * 认证流程（请求进入 → 模块校验 → CallerPrincipalCallback 注入调用者身份 →
 * AuthStatus.SUCCESS 返回 → 响应/清理生命周期收尾），并核验全链路副作用。
 *
 * 测试结构：10 个测试用例（E2E-1..E2E-10），每例独立 TEST PASS/FAIL 判定，
 * 汇总输出 E2E TEST SUMMARY，任一用例失败进程退出码为 1。
 * 该测试不依赖任何第三方认证实现——纯 API jar 即可运行（容器自带工厂实现，
 * 与 WildFly/GlassFish 等真实容器把工厂实现装进环境的方式一致）。
 */
import java.util.HashMap;
import java.util.Map;

import javax.security.auth.Subject;
import javax.security.auth.callback.Callback;
import javax.security.auth.callback.CallbackHandler;

import jakarta.security.auth.message.AuthException;
import jakarta.security.auth.message.AuthStatus;
import jakarta.security.auth.message.MessageInfo;
import jakarta.security.auth.message.MessagePolicy;
import jakarta.security.auth.message.callback.CallerPrincipalCallback;
import jakarta.security.auth.message.config.AuthConfigFactory;
import jakarta.security.auth.message.config.AuthConfigProvider;
import jakarta.security.auth.message.config.ClientAuthConfig;
import jakarta.security.auth.message.config.RegistrationListener;
import jakarta.security.auth.message.config.ServerAuthConfig;
import jakarta.security.auth.message.config.ServerAuthContext;
import jakarta.security.auth.message.module.ServerAuthModule;

public class TestAuthFlow {

    /** 最小 AuthConfigFactory 实现（容器角色）：内存注册表，覆盖全部抽象方法 */
    public static class MiniAuthConfigFactory extends AuthConfigFactory {
        private final Map<String, AuthConfigProvider> providers = new HashMap<String, AuthConfigProvider>();
        private final Map<String, String> scope = new HashMap<String, String>();
        private int counter;

        public AuthConfigProvider getConfigProvider(String layer, String appContext,
                                                    RegistrationListener listener) {
            String want = layer + "|" + appContext;
            for (Map.Entry<String, AuthConfigProvider> e : providers.entrySet()) {
                if (want.equals(scope.get(e.getKey()))) {
                    return e.getValue();
                }
            }
            return null;
        }

        public String registerConfigProvider(String className, Map<String, String> properties,
                                             String layer, String appContext, String description) {
            throw new UnsupportedOperationException("className-based registration not used in this test");
        }

        public String registerConfigProvider(AuthConfigProvider provider, String layer,
                                             String appContext, String description) {
            String id = "reg-" + (++counter);
            providers.put(id, provider);
            scope.put(id, layer + "|" + appContext);
            return id;
        }

        public String registerServerAuthModule(ServerAuthModule serverAuthModule, Object context) {
            return null; // 旧式模块级注册本用例不使用
        }

        public void removeServerAuthModule(Object context) {
        }

        public boolean removeRegistration(String registrationID) {
            scope.remove(registrationID);
            return providers.remove(registrationID) != null;
        }

        public String[] detachListener(RegistrationListener listener, String layer, String appContext) {
            return new String[0];
        }

        public String[] getRegistrationIDs(AuthConfigProvider provider) {
            java.util.List<String> ids = new java.util.ArrayList<String>();
            for (Map.Entry<String, AuthConfigProvider> e : providers.entrySet()) {
                if (e.getValue() == provider) {
                    ids.add(e.getKey());
                }
            }
            return ids.toArray(new String[0]);
        }

        public RegistrationContext getRegistrationContext(String registrationID) {
            if (!providers.containsKey(registrationID)) {
                return null;
            }
            return new RegistrationContext() {
                public String getMessageLayer() {
                    return scope.get(registrationID).split("\\|")[0];
                }

                public String getAppContext() {
                    return scope.get(registrationID).split("\\|")[1];
                }

                public String getDescription() {
                    return "in-memory test registration";
                }

                public boolean isPersistent() {
                    return false;
                }
            };
        }

        public void refresh() {
        }
    }

    /** 最小 ServerAuthModule 实现：回调注入调用者身份，返回 SUCCESS */
    public static class TestServerAuthModule implements ServerAuthModule {
        private CallbackHandler handler;

        public void initialize(MessagePolicy requestPolicy, MessagePolicy responsePolicy,
                               CallbackHandler handler, Map<String, Object> options)
                throws AuthException {
            this.handler = handler;
        }

        public Class<?>[] getSupportedMessageTypes() {
            return new Class<?>[] { String.class };
        }

        public AuthStatus validateRequest(MessageInfo messageInfo, Subject clientSubject,
                                          Subject serviceSubject) throws AuthException {
            try {
                handler.handle(new Callback[] { new CallerPrincipalCallback(clientSubject, "alice") });
            } catch (Exception e) {
                throw new AuthException("CallbackHandler.handle failed: " + e.getMessage());
            }
            messageInfo.getMap().put("auth.module", "TestServerAuthModule");
            return AuthStatus.SUCCESS;
        }
    }

    /** 最小 ServerAuthContext 实现：委托给模块 */
    public static class TestServerAuthContext implements ServerAuthContext {
        private final ServerAuthModule module;

        TestServerAuthContext(ServerAuthModule module) {
            this.module = module;
        }

        public AuthStatus validateRequest(MessageInfo messageInfo, Subject clientSubject,
                                          Subject serviceSubject) throws AuthException {
            return module.validateRequest(messageInfo, clientSubject, serviceSubject);
        }
    }

    /** 最小 ServerAuthConfig 实现：按 authContextID 装配模块与上下文 */
    public static class TestServerAuthConfig implements ServerAuthConfig {
        private final String layer;
        private final String appContext;
        private final CallbackHandler handler;

        TestServerAuthConfig(String layer, String appContext, CallbackHandler handler) {
            this.layer = layer;
            this.appContext = appContext;
            this.handler = handler;
        }

        public ServerAuthContext getAuthContext(String authContextID, Subject serviceSubject,
                                                Map<String, Object> properties)
                throws AuthException {
            TestServerAuthModule module = new TestServerAuthModule();
            module.initialize(null, null, handler, properties);
            return new TestServerAuthContext(module);
        }

        public String getMessageLayer() {
            return layer;
        }

        public String getAppContext() {
            return appContext;
        }

        public String getAuthContextID(MessageInfo messageInfo) {
            return "test-auth";
        }

        public void refresh() {
        }

        public boolean isProtected() {
            return true;
        }
    }

    /** 最小 AuthConfigProvider 实现：本用例只走服务端认证流程 */
    public static class TestAuthConfigProvider implements AuthConfigProvider {
        public ClientAuthConfig getClientAuthConfig(String layer, String appContext,
                                                    CallbackHandler handler) throws AuthException {
            return null;
        }

        public ServerAuthConfig getServerAuthConfig(String layer, String appContext,
                                                    CallbackHandler handler) throws AuthException {
            return new TestServerAuthConfig(layer, appContext, handler);
        }

        public void refresh() {
        }
    }

    /** 最小 MessageInfo 实现：请求/响应载体 + 模块属性 map */
    public static class TestMessageInfo implements MessageInfo {
        private Object request;
        private Object response;
        private final Map<String, Object> map = new HashMap<String, Object>();

        public Object getRequestMessage() {
            return request;
        }

        public Object getResponseMessage() {
            return response;
        }

        public void setRequestMessage(Object request) {
            this.request = request;
        }

        public void setResponseMessage(Object response) {
            this.response = response;
        }

        public Map<String, Object> getMap() {
            return map;
        }
    }

    private static int passed = 0;
    private static int failed = 0;

    /** 测试状态：10 个测试用例共享的流程上下文 */
    private static AuthConfigFactory factory;
    private static String regId;
    private static AuthConfigProvider provider;
    private static CallbackHandler handler;
    private static ServerAuthConfig config;
    private static Subject serviceSubject;
    private static ServerAuthContext context;
    private static TestMessageInfo info;
    private static Subject clientSubject;

    /** 测试用例接口：允许抛出受检异常（SPI 方法声明 AuthException），由执行器统一判定 */
    private interface TestCase {
        void run() throws Exception;
    }

    /** 测试执行器：每个测试用例独立判定 TEST PASS/FAIL，异常不中断后续用例 */
    private static void runCase(String caseName, TestCase body) {
        try {
            body.run();
            passed++;
            System.out.println("TEST PASS: " + caseName);
        } catch (Throwable t) {
            failed++;
            System.out.println("TEST FAIL: " + caseName + " ("
                    + t.getClass().getSimpleName() + ": " + t.getMessage() + ")");
        }
    }

    /** E2E-1 容器安装工厂实现并取回（容器角色） */
    private static void e2e1() throws Exception {
        AuthConfigFactory.setFactory(new MiniAuthConfigFactory());
        factory = AuthConfigFactory.getFactory();
        if (factory == null) {
            throw new AssertionError("AuthConfigFactory.getFactory() returned null");
        }
    }

    /** E2E-2 注册认证配置提供者 */
    private static void e2e2() throws Exception {
        provider = new TestAuthConfigProvider();
        regId = factory.registerConfigProvider(provider, "HttpServlet", "test-app",
                "E2E consumer test");
        if (regId == null) {
            throw new AssertionError("registerConfigProvider returned null");
        }
    }

    /** E2E-3 通过工厂取回提供者（RegistrationListener 关联，容器常规路径） */
    private static void e2e3() throws Exception {
        RegistrationListener listener = new RegistrationListener() {
            public void notify(String layer, String appContext) {
            }
        };
        AuthConfigProvider fetched = factory.getConfigProvider("HttpServlet", "test-app", listener);
        if (fetched == null) {
            throw new AssertionError("getConfigProvider returned null");
        }
    }

    /** E2E-4 获取 ServerAuthConfig，核验消息层契约 */
    private static void e2e4() throws Exception {
        // 容器侧 CallbackHandler：按 JSR-196 契约处理 CallerPrincipalCallback，
        // 把模块声明的调用者身份写入 clientSubject（真实容器职责）
        handler = new CallbackHandler() {
            public void handle(Callback[] callbacks)
                    throws java.io.IOException, javax.security.auth.callback.UnsupportedCallbackException {
                for (Callback cb : callbacks) {
                    if (cb instanceof CallerPrincipalCallback) {
                        CallerPrincipalCallback cpc = (CallerPrincipalCallback) cb;
                        final String name;
                        if (cpc.getPrincipal() != null) {
                            name = cpc.getPrincipal().getName();
                        } else {
                            name = cpc.getName();
                        }
                        cpc.getSubject().getPrincipals().add(new java.security.Principal() {
                            public String getName() {
                                return name;
                            }
                        });
                    }
                }
            }
        };
        config = provider.getServerAuthConfig("HttpServlet", "test-app", handler);
        if (!"HttpServlet".equals(config.getMessageLayer())) {
            throw new AssertionError("message layer mismatch: " + config.getMessageLayer());
        }
    }

    /** E2E-5 核验保护性契约 */
    private static void e2e5() throws Exception {
        if (config == null || !config.isProtected()) {
            throw new AssertionError("isProtected() must be true");
        }
    }

    /** E2E-6 获取认证上下文 */
    private static void e2e6() throws Exception {
        serviceSubject = new Subject();
        context = config.getAuthContext("test-auth", serviceSubject,
                new HashMap<String, Object>());
        if (context == null) {
            throw new AssertionError("getAuthContext returned null");
        }
    }

    /** E2E-7 跑通认证流程：请求进入 → 模块校验 → 返回状态 */
    private static void e2e7() throws Exception {
        info = new TestMessageInfo();
        info.setRequestMessage("GET /protected");
        clientSubject = new Subject();
        AuthStatus status = context.validateRequest(info, clientSubject, serviceSubject);
        if (status != AuthStatus.SUCCESS) {
            throw new AssertionError("expected SUCCESS, got " + status);
        }
    }

    /** E2E-8 核验端到端副作用：CallerPrincipalCallback 把调用者身份注入 clientSubject */
    private static void e2e8() throws Exception {
        boolean hasPrincipal = false;
        for (java.security.Principal p : clientSubject.getPrincipals()) {
            if ("alice".equals(p.getName())) {
                hasPrincipal = true;
                break;
            }
        }
        if (!hasPrincipal) {
            throw new AssertionError("principal alice not injected via CallerPrincipalCallback");
        }
    }

    /** E2E-9 核验模块处理标记进入 MessageInfo map */
    private static void e2e9() throws Exception {
        if (!"TestServerAuthModule".equals(info.getMap().get("auth.module"))) {
            throw new AssertionError("module marker missing in MessageInfo map");
        }
    }

    /** E2E-10 响应/清理生命周期走完 + 注销注册 */
    private static void e2e10() throws Exception {
        context.secureResponse(info, serviceSubject);
        context.cleanSubject(info, clientSubject);
        if (!factory.removeRegistration(regId)) {
            throw new AssertionError("removeRegistration failed");
        }
    }

    public static void main(String[] args) {
        runCase("E2E-1 AuthConfigFactory installed and retrieved", TestAuthFlow::e2e1);
        runCase("E2E-2 provider registered via factory", TestAuthFlow::e2e2);
        runCase("E2E-3 provider retrieved from factory", TestAuthFlow::e2e3);
        runCase("E2E-4 ServerAuthConfig contract (layer=HttpServlet)", TestAuthFlow::e2e4);
        runCase("E2E-5 isProtected contract", TestAuthFlow::e2e5);
        runCase("E2E-6 ServerAuthContext acquired", TestAuthFlow::e2e6);
        runCase("E2E-7 validateRequest -> AuthStatus.SUCCESS", TestAuthFlow::e2e7);
        runCase("E2E-8 CallerPrincipalCallback injected principal alice into clientSubject",
                TestAuthFlow::e2e8);
        runCase("E2E-9 module marker propagated through MessageInfo map", TestAuthFlow::e2e9);
        runCase("E2E-10 secureResponse/cleanSubject lifecycle + removeRegistration",
                TestAuthFlow::e2e10);

        System.out.println("E2E TEST SUMMARY: " + passed + " passed, " + failed + " failed");
        System.out.println((passed == 10 && failed == 0)
                ? "PASS: E2E consumer test (factory -> provider -> config -> context"
                        + " -> validateRequest -> SUCCESS -> principal injection -> lifecycle)"
                : "FAIL: E2E consumer test");
        System.exit(failed == 0 ? 0 : 1);
    }
}
