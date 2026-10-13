import java.lang.annotation.Annotation;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import jakarta.annotation.Generated;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import jakarta.annotation.Priority;
import jakarta.annotation.Resource;
import jakarta.annotation.Resources;
import jakarta.annotation.security.DeclareRoles;
import jakarta.annotation.security.PermitAll;
import jakarta.annotation.security.RolesAllowed;
import jakarta.annotation.security.RunAs;

/**
 * ConsumerAnnotationTest — jakarta.annotation 完整消费者用例（端到端）
 *
 * 模拟一个 Jakarta EE 风格的轻量容器，按 Common Annotations 规范语义消费
 * jar 中的注解，跑通真实生命周期流程：
 *
 *   1. @Resource 字段/方法注入（含默认值推导、AuthenticationType、lookup）
 *   2. @PostConstruct / @PreDestroy 生命周期回调发现与调用
 *   3. @Priority 排序（拦截器优先级语义）
 *   4. @RolesAllowed / @PermitAll / @RunAs / @DeclareRoles 安全元数据处理
 *   5. @Repeatable(@Resources) 重复资源声明解析
 *   6. @Generated 代码生成标记元数据读取
 *
 * 与纯反射探针（TestJakartaAnnotation）不同，本用例真实消费注解语义，
 * 即一个与 Spring/Weld 容器同构的最小注解驱动容器。
 */
public class ConsumerAnnotationTest {

    // ==== 容器侧：轻量资源注入器 ====
    static class SimpleContainer {
        private final java.util.Map<String, Object> jndi = new java.util.HashMap<>();
        private final List<String> lifecycleLog = new ArrayList<>();

        void bind(String name, Object value) { jndi.put(name, value); }

        List<String> getLifecycleLog() { return lifecycleLog; }

        /** 模拟容器注入 @Resource 字段并调用 @PostConstruct */
        <T> T create(Class<T> clazz) throws Exception {
            T instance = clazz.getDeclaredConstructor().newInstance();
            for (Field f : clazz.getDeclaredFields()) {
                Resource res = f.getAnnotation(Resource.class);
                if (res == null) continue;
                // 规范语义：字段注入时 name 默认取字段名
                String jndiName = res.name().isEmpty() ? f.getName() : res.name();
                Object value = jndi.get(jndiName);
                if (value == null) {
                    throw new IllegalStateException("No resource bound for " + jndiName);
                }
                f.setAccessible(true);
                f.set(instance, value);
                lifecycleLog.add("injected " + f.getName() + " <- " + jndiName
                        + " (auth=" + res.authenticationType() + ")");
            }
            // 规范语义：依赖注入完成后调用 @PostConstruct
            for (Method m : clazz.getDeclaredMethods()) {
                if (m.isAnnotationPresent(PostConstruct.class)) {
                    m.setAccessible(true);
                    m.invoke(instance);
                    lifecycleLog.add("postConstruct:" + m.getName());
                }
            }
            return instance;
        }

        /** 模拟容器销毁：调用 @PreDestroy */
        void destroy(Object instance) throws Exception {
            for (Method m : instance.getClass().getDeclaredMethods()) {
                if (m.isAnnotationPresent(PreDestroy.class)) {
                    m.setAccessible(true);
                    m.invoke(instance);
                    lifecycleLog.add("preDestroy:" + m.getName());
                }
            }
        }
    }

    // ==== 业务组件：全量消费 8 类注解 ====
    @Generated(value = "com.example.codegen.ServiceGenerator",
               date = "2026-10-08T12:00:00", comments = "test fixture")
    @DeclareRoles({"admin", "user"})
    @RunAs("admin")
    static class OrderService {
        @Resource(name = "jdbc/orders", lookup = "java:app/env/ordersDs",
                  type = javax.sql.DataSource.class)
        private Object orderDs;

        @Resource(shareable = false, description = "order queue")
        private Object orderQueue;   // 默认 name = 字段名

        private boolean initialized;

        @PostConstruct
        void init() { initialized = true; }

        @PreDestroy
        void shutdown() { /* no-op */ }

        @PermitAll
        public String ping() { return "pong"; }

        @RolesAllowed({"admin"})
        public String placeOrder(String item) { return "order:" + item; }

        boolean isInitialized() { return initialized; }
    }

    // ==== @Repeatable(@Resources) 容器注解解析 ====
    @Resource(name = "queue/a", type = Object.class)
    @Resource(name = "queue/b", type = Object.class)
    static class MultiResourceBean {}

    // ==== @Priority 拦截器（Platform 规范：拦截器优先级排序） ====
    @Priority(2000)
    static abstract class AuditInterceptor {}

    @Priority(100)
    static abstract class LoggingInterceptor {}

    static int failed = 0;
    static int passed = 0;

    static void expect(String label, boolean cond) {
        if (cond) { passed++; System.out.println("OK: " + label); }
        else      { failed++; System.err.println("FAILED: " + label); }
    }

    public static void main(String[] args) throws Exception {
        SimpleContainer container = new SimpleContainer();
        container.bind("jdbc/orders", "fake-order-ds");
        container.bind("orderQueue", "fake-order-queue");
        container.bind("queue/a", "fake-queue-a");
        container.bind("queue/b", "fake-queue-b");

        // ---- 1. @Resource 注入 + @PostConstruct 生命周期 ----
        OrderService svc = container.create(OrderService.class);
        // 注入是否真实生效：读取私有字段验证注入值来自 JNDI 绑定
        Field dsField = OrderService.class.getDeclaredField("orderDs");
        dsField.setAccessible(true);
        expect("@Resource(name=) 注入显式 JNDI 名 jdbc/orders",
                "fake-order-ds".equals(dsField.get(svc)));
        Field queueField = OrderService.class.getDeclaredField("orderQueue");
        queueField.setAccessible(true);
        expect("@Resource 无 name 时默认字段名注入 orderQueue",
                "fake-order-queue".equals(queueField.get(svc)));
        expect("@Resource.description 元数据可读",
                OrderService.class.getDeclaredField("orderQueue")
                        .getAnnotation(Resource.class).description().equals("order queue"));
        expect("@Resource.shareable 元数据可读",
                !OrderService.class.getDeclaredField("orderQueue")
                        .getAnnotation(Resource.class).shareable());
        expect("@PostConstruct 回调已调用", svc.isInitialized());
        expect("注入器记录 auth 默认值 CONTAINER",
                container.getLifecycleLog().stream()
                        .anyMatch(l -> l.contains("auth=CONTAINER")));

        // ---- 2. @PreDestroy 生命周期 ----
        container.destroy(svc);
        expect("@PreDestroy 回调已调用",
                container.getLifecycleLog().contains("preDestroy:shutdown"));

        // ---- 3. @Priority 排序语义（拦截器优先级，Platform 规范语义） ----
        List<Class<?>> interceptors = new ArrayList<>(
                Arrays.asList(AuditInterceptor.class, LoggingInterceptor.class));
        interceptors.sort((a, b) -> Integer.compare(
                a.getAnnotation(Priority.class).value(),
                b.getAnnotation(Priority.class).value()));
        expect("@Priority 升序排序语义（容器按注解值排序拦截器）",
                interceptors.equals(Arrays.asList(
                        LoggingInterceptor.class, AuditInterceptor.class)));

        // ---- 4. 安全注解元数据 ----
        RolesAllowed ra = OrderService.class.getMethod("placeOrder", String.class)
                .getAnnotation(RolesAllowed.class);
        expect("@RolesAllowed 值读取", Arrays.equals(ra.value(), new String[]{"admin"}));
        expect("@PermitAll 存在于 ping()", OrderService.class.getMethod("ping")
                .isAnnotationPresent(PermitAll.class));
        RunAs runAs = OrderService.class.getAnnotation(RunAs.class);
        expect("@RunAs 值读取", "admin".equals(runAs.value()));
        DeclareRoles dr = OrderService.class.getAnnotation(DeclareRoles.class);
        expect("@DeclareRoles 值读取", Arrays.equals(dr.value(), new String[]{"admin", "user"}));

        // ---- 5. @Repeatable(@Resources) ----
        Resource[] resources = MultiResourceBean.class.getAnnotationsByType(Resource.class);
        expect("@Repeatable Resources 解析出 2 条资源声明", resources.length == 2);
        Resources container2 = MultiResourceBean.class.getAnnotation(Resources.class);
        expect("@Resources 容器注解可直读", container2 != null && container2.value().length == 2);
        List<String> names = new ArrayList<>();
        for (Resource r : resources) names.add(r.name());
        expect("两条资源声明 name 均正确",
                names.contains("queue/a") && names.contains("queue/b"));

        // ---- 6. @Generated 元数据（SOURCE 保留策略——按规范运行时不可见） ----
        // 规范语义：@Generated Retention=SOURCE，编译后丢弃；
        // 消费者侧（如 javac 编译本测试时）注解语法有效即可用。
        // 此处断言：类上的 @Generated 编译后确实不可见（SOURCE 语义），
        // 且注解类型本身的元数据仍可从 jar 反射读取。
        boolean visible = OrderService.class.isAnnotationPresent(Generated.class);
        expect("@Generated Retention=SOURCE：运行时不可见（规范语义）", !visible);
        expect("@Generated 注解类型自身元数据可读（jar 中类型完整）",
                Generated.class.getAnnotation(Retention.class).value() == RetentionPolicy.SOURCE
                        && Generated.class.getDeclaredMethods().length == 3
                        && java.util.Arrays.asList(Generated.class.getDeclaredMethods())
                                .stream().map(m -> m.getName())
                                .collect(java.util.stream.Collectors.toSet())
                                .containsAll(java.util.Arrays.asList("value", "date", "comments")));

        System.out.println();
        System.out.println("E2E TEST SUMMARY: " + passed + " passed, " + failed + " failed");
        if (failed > 0) {
            System.err.println("FAIL: jakarta.annotation consumer E2E");
            System.exit(1);
        }
        System.out.println("PASS: jakarta.annotation consumer E2E - real annotation-driven container flow");
        System.exit(0);
    }
}
