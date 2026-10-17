/**
 * ConsumerInjectTest — jakarta.inject 完整消费者用例（端到端）
 *
 * 用 jakarta.inject API 实现一个最小 DI 容器，跑通真实注入流程：
 *   注册提供者 → 创建消费对象 → 字段注入（@Inject/@Named）→ @Singleton 单例契约
 *   → 业务方法产出可观测结果。
 *
 * 与纯反射断言（TestJakartaInject）不同，本用例真正消费 API 语义：
 * 注解驱动注入 + 限定符消歧 + 单例作用域 + Provider 工厂抽象，
 * 即一个与 Guice/Weld 同构的最小 JSR-330 容器。
 */
import jakarta.inject.Inject;
import jakarta.inject.Named;
import jakarta.inject.Provider;
import jakarta.inject.Singleton;

import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.Map;

public class ConsumerInjectTest {

    // 业务对象：被注入的依赖（@Singleton 作用域）
    @Singleton
    static class Engine {
        String start() { return "vroom"; }
    }

    // 业务对象：消费方（通过 @Inject 声明依赖）
    static class Car {
        @Inject Engine engine;
        @Inject @Named("driver") String driver;
        String drive() { return engine.start() + " by " + driver; }
    }

    // 最小 DI 容器：只消费 jakarta.inject 的注解与 Provider 契约
    static class MiniInjector {
        private final Map<String, Provider<?>> providers = new HashMap<>();
        private final Map<String, Object> singletons = new HashMap<>();

        void bind(Class<?> key, Provider<?> provider) {
            providers.put(key.getName(), provider);
        }

        void bindNamed(String name, Provider<?> provider) {
            providers.put(name, provider);
        }

        void injectInto(Object instance) throws Exception {
            for (Field f : instance.getClass().getDeclaredFields()) {
                if (!f.isAnnotationPresent(Inject.class)) continue;
                Named named = f.getAnnotation(Named.class);
                String key = (named != null) ? named.value() : f.getType().getName();
                Provider<?> provider = providers.get(key);
                if (provider == null) {
                    throw new IllegalStateException("No provider bound for " + key);
                }
                Object value;
                if (f.getType().isAnnotationPresent(Singleton.class)) {
                    value = singletons.computeIfAbsent(key, k -> provider.get());
                } else {
                    value = provider.get();
                }
                f.setAccessible(true);
                f.set(instance, value);
            }
        }
    }

    public static void main(String[] args) throws Exception {
        MiniInjector injector = new MiniInjector();
        injector.bind(Engine.class, new Provider<Engine>() {
            public Engine get() { return new Engine(); }
        });
        injector.bindNamed("driver", new Provider<String>() {
            public String get() { return "test-driver"; }
        });

        // 步骤 1: 创建两个消费对象并完成注入
        Car car1 = new Car();
        Car car2 = new Car();
        injector.injectInto(car1);
        injector.injectInto(car2);
        System.out.println("OK: injection completed for 2 consumers");

        // 步骤 2: @Singleton 契约——两车共享同一引擎实例
        if (car1.engine != car2.engine) {
            System.err.println("FAIL: @Singleton engine not shared across consumers");
            System.exit(1);
        }
        System.out.println("OK: @Singleton scope contract (shared Engine instance)");

        // 步骤 3: 业务流程端到端——注入的依赖真实可用
        String out = car1.drive();
        if (!"vroom by test-driver".equals(out)) {
            System.err.println("FAIL: drive() produced unexpected result: " + out);
            System.exit(1);
        }
        System.out.println("OK: consumer DI flow end-to-end: " + out);

        // 步骤 4: @Named 限定符消歧——同类型依赖按名字选中绑定
        if (!"test-driver".equals(car1.driver)) {
            System.err.println("FAIL: @Named qualifier did not select bound provider");
            System.exit(1);
        }
        System.out.println("OK: @Named qualifier disambiguation");

        // 步骤 5: Provider 契约——绑定的提供者是 jakarta.inject.Provider 工厂
        if (!(injector.providers.get(Engine.class.getName()) instanceof jakarta.inject.Provider)) {
            System.err.println("FAIL: bound provider is not a jakarta.inject.Provider");
            System.exit(1);
        }
        System.out.println("OK: Provider contract (jakarta.inject.Provider as factory)");

        System.out.println("PASS: jakarta.inject consumer E2E - real DI injection flow");
    }
}
