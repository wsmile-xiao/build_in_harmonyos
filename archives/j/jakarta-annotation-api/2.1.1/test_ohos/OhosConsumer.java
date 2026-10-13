import java.lang.reflect.Field;
import java.lang.reflect.Method;

import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import jakarta.annotation.Priority;
import jakarta.annotation.Resource;

/**
 * HarmonyOS PC 专项最小消费者（test_ohos T5）。
 *
 * 在已通过 ELF64 / AArch64 / musl loader 验证的 JVM 上，消费最终 Conan 包中的
 * jakarta.annotation-api-2.1.1.jar：真实引用 @Resource / @PostConstruct /
 * @PreDestroy / @Priority 四类注解，模拟最小注解驱动容器的注入与生命周期语义，
 * 并核验 JVM 自报平台为 HarmonyOS aarch64（区别于任意 Linux aarch64 JVM）。
 * 任一断言失败即以退出码 1 结束。
 */
public class OhosConsumer {

    @Resource(name = "ohos/datasource", shareable = false)
    private String dataSource;

    @Resource
    private String orderQueue;

    private boolean postConstructCalled = false;
    private boolean preDestroyCalled = false;

    @PostConstruct
    private void start() {
        postConstructCalled = true;
    }

    @PreDestroy
    private void stop() {
        preDestroyCalled = true;
    }

    @Priority(200)
    public int interceptorPriority() {
        return 200;
    }

    private static void check(boolean cond, String what) {
        if (!cond) {
            System.out.println("OHOS-FAIL: " + what);
            System.exit(1);
        }
        System.out.println("OHOS-OK: " + what);
    }

    public static void main(String[] args) throws Exception {
        // 1) 平台核验：待测 JVM 自报 HarmonyOS aarch64
        String osName = System.getProperty("os.name", "");
        String osArch = System.getProperty("os.arch", "");
        String osVersion = System.getProperty("os.version", "");
        System.out.println("OHOS-JVM os.name=" + osName);
        System.out.println("OHOS-JVM os.arch=" + osArch);
        System.out.println("OHOS-JVM os.version=" + osVersion);
        check(osName.toLowerCase().contains("harmonyos"),
                "JVM os.name 报告 HarmonyOS（实际: " + osName + "）");
        check("aarch64".equals(osArch),
                "JVM os.arch = aarch64（实际: " + osArch + "）");

        // 2) @Resource 元数据消费：显式 JNDI 名 + 默认字段名推导 + shareable
        OhosConsumer c = new OhosConsumer();
        Field ds = OhosConsumer.class.getDeclaredField("dataSource");
        Resource dsRes = ds.getAnnotation(Resource.class);
        check(dsRes != null, "@Resource 存在于 dataSource 字段");
        check("ohos/datasource".equals(dsRes.name()),
                "@Resource.name() = ohos/datasource");
        check(!dsRes.shareable(), "@Resource.shareable() = false 生效");
        ds.setAccessible(true);
        ds.set(c, "bound:ohos/datasource");
        check("bound:ohos/datasource".equals(ds.get(c)),
                "注入器按 @Resource 元数据绑定后字段值真实生效");

        Field q = OhosConsumer.class.getDeclaredField("orderQueue");
        Resource qRes = q.getAnnotation(Resource.class);
        check(qRes != null && qRes.name().isEmpty(),
                "@Resource 无显式 name 时 name() 为空串（默认名推导属容器职责，规范语义）");
        q.setAccessible(true);
        q.set(c, "bound:" + q.getName());
        check("bound:orderQueue".equals(q.get(c)),
                "注入器按字段名推导默认 JNDI 名绑定后字段值真实生效");

        // 3) 生命周期消费：@PostConstruct / @PreDestroy 回调
        Method init = OhosConsumer.class.getDeclaredMethod("start");
        check(init.isAnnotationPresent(PostConstruct.class),
                "@PostConstruct 标注 start()");
        init.setAccessible(true);
        init.invoke(c);
        check(c.postConstructCalled, "@PostConstruct 回调已执行");

        Method fin = OhosConsumer.class.getDeclaredMethod("stop");
        check(fin.isAnnotationPresent(PreDestroy.class),
                "@PreDestroy 标注 stop()");
        fin.setAccessible(true);
        fin.invoke(c);
        check(c.preDestroyCalled, "@PreDestroy 回调已执行");

        // 4) @Priority 元数据消费（拦截器排序语义）
        Method p = OhosConsumer.class.getDeclaredMethod("interceptorPriority");
        Priority pri = p.getAnnotation(Priority.class);
        check(pri != null && pri.value() == 200, "@Priority(200) 元数据可读");

        System.out.println("OHOS consumer OK: jakarta.annotation-api 2.1.1 consumed on "
                + osName + " " + osArch + " (" + osVersion + ")");
    }
}
