// R34: 实际调用被测包 API 的测试——模板加载/渲染/值绑定/过滤器四类核心路径
#include <iostream>
#include <string>

#include <jinja2cpp/template.h>
#include <jinja2cpp/value.h>

int main()
{
    int failures = 0;

    // 1) 纯文本模板渲染（Load 返回 expected，value() 判定）
    {
        jinja2::Template tpl;
        auto loadRes = tpl.Load("Hello World from Parser!");
        if (!loadRes)
        {
            std::cerr << "[FAIL] plain text load: " << loadRes.error() << std::endl;
            failures++;
        }
        std::string res = tpl.RenderAsString({});
        if (res != "Hello World from Parser!")
        {
            std::cerr << "[FAIL] plain text render, got: " << res << std::endl;
            failures++;
        }
        else
        {
            std::cout << "[ok] plain text render" << std::endl;
        }
    }

    // 2) 值替换 {{ name }} + 过滤器 upper
    {
        jinja2::Template tpl;
        auto loadRes = tpl.Load("{{ name }} is {{ age }}; upper: {{ name | upper }}");
        if (!loadRes)
        {
            std::cerr << "[FAIL] substitution load" << std::endl;
            failures++;
        }
        jinja2::ValuesMap params;
        params["name"] = "harmony";
        params["age"] = 6;
        std::string res = tpl.RenderAsString(params);
        if (res != "harmony is 6; upper: HARMONY")
        {
            std::cerr << "[FAIL] substitution render, got: " << res << std::endl;
            failures++;
        }
        else
        {
            std::cout << "[ok] substitution + upper filter" << std::endl;
        }
    }

    // 3) for 循环 + 列表值绑定
    {
        jinja2::Template tpl;
        auto loadRes = tpl.Load("{% for i in items %}{{ i }};{% endfor %}");
        if (!loadRes)
        {
            std::cerr << "[FAIL] for load" << std::endl;
            failures++;
        }
        jinja2::ValuesMap params;
        params["items"] = jinja2::ValuesList{1, 2, 3};
        std::string res = tpl.RenderAsString(params);
        if (res != "1;2;3;")
        {
            std::cerr << "[FAIL] for render, got: " << res << std::endl;
            failures++;
        }
        else
        {
            std::cout << "[ok] for loop render" << std::endl;
        }
    }

    // 4) if 条件 + 比较表达式
    {
        jinja2::Template tpl;
        auto loadRes = tpl.Load("{% if a > b %}gt{% else %}le{% endif %}");
        if (!loadRes)
        {
            std::cerr << "[FAIL] if load" << std::endl;
            failures++;
        }
        jinja2::ValuesMap params;
        params["a"] = 10;
        params["b"] = 3;
        std::string res = tpl.RenderAsString(params);
        if (res != "gt")
        {
            std::cerr << "[FAIL] if render, got: " << res << std::endl;
            failures++;
        }
        else
        {
            std::cout << "[ok] if comparison render" << std::endl;
        }
    }

    if (failures == 0)
    {
        std::cout << "ALL TESTS PASSED" << std::endl;
        return 0;
    }
    std::cerr << failures << " tests failed" << std::endl;
    return 1;
}
