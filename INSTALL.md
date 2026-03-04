# KB Exporter 安装指南

## 简介

KB Exporter 是一个用于将 CVTE 知识库 (kb.cvte.com) 页面导出为 Markdown 文档的工具。

### 功能特性

- 自动检测 kb.cvte.com 链接并询问是否导出
- 批量导出多个页面
- 自动下载图片并修正引用
- 使用文章标题作为文件名
- 从 `<div id="main-content" class="wiki-content">` 提取正文内容
- Cookie 过期自动检测和更新

---

## 安装步骤

### 1. 安装 Python 依赖

```bash
pip3 install requests beautifulsoup4
```

**说明**：
- `requests` - 用于 HTTP 请求和获取页面内容
- `beautifulsoup4` - 用于解析 HTML 和提取内容

### 2. 安装 Skill

将 `kb-exporter.skill` 文件复制到 Claude Code 的 skills 目录：

```bash
cp kb-exporter.skill ~/.claude/skills/
```

---

## 使用方法

安装后，直接在对话中分享 kb.cvte.com 链接即可：

```
你: https://kb.cvte.com/pages/viewpage.action?pageId=495126015

Claude: 检测到 KB 链接，是否要导出为 Markdown 文档？

你: 是

Claude: [检查 cookie 状态]
     [如过期则询问新的 JSESSIONID]
     [执行导出并下载图片]
```

### Cookie 配置

当首次使用时，如果检测到 cookie 无效或过期，会提示你提供 JSESSIONID：

```
Claude: Cookie 已过期，请提供新的 JSESSIONID

你: JSESSIONID=ABC123...

Claude: ✓ Cookie 已更新并保存
```

**获取 JSESSIONID 的方法**：
1. 在浏览器中访问 https://kb.cvte.com 并登录
2. 打开开发者工具 (F12) → Application → Cookies
3. 找到 `JSESSIONID` 并复制其值

---

## 输出格式

导出的文件包含：

- **文件名**: `{文章标题}.md`（自动清理特殊字符）
- **Frontmatter**: 包含标题、来源链接、页面ID、图片数量
- **图片**: 下载到 `./images/` 子目录
- **图片引用**: `![图片](images/filename.png)`
- **代码块**: 支持 Confluence 代码格式，自动提取文件名
