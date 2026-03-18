# 通用 Skill - 网页浏览

## 功能
让Agent具备控制浏览器的能力，包括：
- 打开网页
- 点击元素
- 填表单
- 截图
- 执行JavaScript

## 使用方法

```python
from scripts.tools.web_browser import WebBrowser

browser = WebBrowser()

# 打开网页
browser.open("https://github.com")

# 点击元素
browser.click("button.submit")

# 填表单
browser.fill("input[name='q']", "搜索内容")

# 截图
browser.screenshot("page.png")

# 获取页面内容
content = browser.get_content()
```

## 适用场景
- 自动化测试
- 数据抓取
- 网页操作
- 截图留存

## 注意事项
1. 使用后记得关闭浏览器
2. 避免频繁操作被封IP
3. 敏感操作需要登录态
