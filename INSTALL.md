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

## 安装步骤

### 1. 安装 Python 依赖

```bash
pip3 install requests beautifulsoup4
```

或使用 requirements.txt：

```bash
pip3 install -r requirements.txt
```

### 2. 安装 Skill

将 `kb-exporter.skill` 文件复制到 Claude Code 的 skills 目录：

```bash
# macOS/Linux
cp kb-exporter.skill ~/.claude/skills/

# 或指定自定义目录
mkdir -p ~/my-skills
cp kb-exporter.skill ~/my-skills/
```

### 3. 配置认证 Cookie

由于 kb.cvte.com 需要登录，需要设置 JSESSIONID。

**方式一：从浏览器获取**

1. 在浏览器中访问 https://kb.cvte.com 并登录
2. 打开开发者工具 (F12) → Application/Storage → Cookies
3. 找到 `JSESSIONID` 并复制其值
4. 运行命令保存 cookie：

```bash
python3 scripts/export.py --cookie "JSESSIONID=你的值"
```

**方式二：使用浏览器扩展**

1. 安装 "Get cookies.txt LOCALLY" 扩展
   - Chrome: [下载链接](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbanldigppf)
2. 登录后点击扩展图标
3. 复制 JSESSIONID 的值
4. 运行上述命令保存

Cookie 会自动保存到 `~/.kb_cache/cookies.json`

## 使用方法

### 方式 1：通过 Claude Code 使用（推荐）

直接在对话中分享 kb.cvte.com 链接，Claude 会自动检测并处理：

```
你: https://kb.cvte.com/pages/viewpage.action?pageId=495126015

Claude: 检测到 KB 链接，是否要导出为 Markdown 文档？

你: 是

Claude: [检查 cookie 状态]
     [如过期则询问新的 JSESSIONID]
     [执行导出]
```

### 方式 2：命令行直接使用

```bash
# 导出单个页面
python3 scripts/export.py "https://kb.cvte.com/pages/viewpage.action?pageId=495126015"

# 批量导出多个页面
python3 scripts/export.py url1 url2 url3 -o ./output

# 导出到指定目录
python3 scripts/export.py <url> -o ./docs

# 跳过图片下载
python3 scripts/export.py <url> --no-images

# 设置/更新 JSESSIONID
python3 scripts/export.py --cookie "JSESSIONID=ABC123..."

# 检查 cookie 是否有效
python3 scripts/export.py --check-cookie
```

## 输出格式

导出的文件包含：

- **文件名**: `{文章标题}.md`（自动清理特殊字符）
- **Frontmatter**: 包含标题、来源链接、页面ID、图片数量
- **图片**: 下载到 `./images/` 子目录
- **图片引用**: `![图片](images/filename.png)`

## Cookie 管理

**保存位置**: `~/.kb_cache/cookies.json`

**格式**:
```json
{
  "JSESSIONID": "F43652A092599235036F2B0E828C8FBA"
}
```

**更新 Cookie**:
```bash
python3 scripts/export.py --cookie "新的JSESSIONID值"
```

**检查 Cookie 状态**:
```bash
python3 scripts/export.py --check-cookie
```

## 工作流程

当检测到 kb.cvte.com 链接时：

1. 询问用户是否导出
2. 检查 `~/.kb_cache/cookies.json` 是否存在
3. 验证 cookie 是否有效
4. 如果 cookie 过期：
   - 提示用户提供新的 JSESSIONID
   - 自动解析用户输入（支持多种格式）
   - 自动保存到 `~/.kb_cache/cookies.json`
5. 执行导出并下载图片

## 示例

```bash
$ python3 scripts/export.py "https://kb.cvte.com/pages/viewpage.action?pageId=495126015"

==================================================
Exporting: https://kb.cvte.com/pages/viewpage.action?pageId=495126015
==================================================
Page ID: 495126015
Fetching page...
Parsing page...
Title: 离线部署操作指南
Images found: 15

Downloading 15 images...
  [1/15] image2025-6-25_14-23-24.png (137833 bytes)
  [2/15] image2025-6-25_14-34-18.png (119713 bytes)
  ...

Converting to Markdown...

✓ Exported to: 离线部署操作指南.md
  Title: 离线部署操作指南
  Images: 15
```

## 故障排除

### Cookie 相关问题

**"No JSESSIONID found"**
- 运行 `python3 scripts/export.py --cookie "JSESSIONID=你的值"` 设置 cookie

**"Cookie expired"**
- Cookie 已过期，需要更新
- 重新从浏览器获取 JSESSIONID 并运行上述命令

### 图片下载失败

- 检查网络连接
- 验证 cookie 是否有效
- 使用 `--no-images` 跳过图片下载

### 其他问题

**"Could not find content area"**
- 页面结构可能不同，请联系开发者并提供页面 URL

## 文件结构

```
kb-exporter/
├── SKILL.md              # Skill 定义文件
├── scripts/
│   └── export.py         # 导出脚本
├── assets/               # (预留) 资源文件
└── references/           # (预留) 参考文档
```

## 技术支持

如有问题或建议，请联系开发团队。
