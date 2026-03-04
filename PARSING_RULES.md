# KB Exporter 解析逻辑规则

本文档描述了 KB Exporter 从 Confluence 页面解析内容并转换为 Markdown 的核心规则。

---

## 1. 输出目录结构

### 规则
根据文章是否有图片，采用不同的输出结构：

**有图片的文章：**
```
{文章标题}/
├── {文章标题}.md
└── images/
    ├── image1.png
    └── image2.png
```

**无图片的文章：**
```
{文章标题}.md
```

### 实现位置
`scripts/export.py` 第 543-553 行
```python
has_images = download_images and images
if has_images:
    # 创建文章目录和 images 子目录
    article_dir = Path(output_dir) / safe_title
    filepath = article_dir / f"{safe_title}.md"
else:
    # 直接保存到输出目录
    filepath = Path(output_dir) / f"{safe_title}.md"
```

---

## 2. 表格中代码块支持

### 问题背景
Confluence 使用 syntaxhighlighter 插件渲染代码块，HTML 结构复杂：
```html
<div class="code panel pdl conf-macro output-block" data-macro-name="code">
  <div class="codeHeader panelHeader pdl">
    <b class="code-title">标题</b>
  </div>
  <div class="codeContent panelContent pdl">
    <pre class="syntaxhighlighter-pre" data-syntaxhighlighter-params="brush: yml; gutter: false;">
apiVersion: v1
kind: Pod
...
    </pre>
  </div>
</div>
```

### 解析规则

#### 2.1 检测代码块
- 查找 `<div data-macro-name="code">` 属性

#### 2.2 提取代码
优先使用新格式（`<pre>` 元素），回退到旧格式（`<div class="syntaxhighlighter">`）

**新格式解析：**
```python
pre_elem = code_content.find('pre', class_='syntaxhighlighter-pre')
if pre_elem and pre_elem.get('data-syntaxhighlighter-params'):
    params = pre_elem.get('data-syntaxhighlighter-params', '')
    brush_match = re.search(r'brush:\s*(\w+)', params)
    if brush_match:
        lang = brush_match.group(1).lower()
        # 映射常见语言别名
        lang_map = {'yml': 'yaml', 'js': 'javascript', 'ts': 'typescript', 'py': 'python'}
        lang = lang_map.get(lang, lang)
    code_text = pre_elem.get_text()
```

**旧格式解析（向后兼容）：**
```python
syntax_div = code_content.find('div', class_='syntaxhighlighter')
if syntax_div:
    classes = syntax_div.get('class', [])
    language_map = ['yml', 'yaml', 'bash', ...]
    for c in classes:
        if c.lower() in language_map:
            lang = c.lower()
            break
    lines = syntax_div.find_all('div', class_=lambda x: 'line' in ' '.join(x))
    # 从 div.line > code 中提取文本
```

#### 2.3 Markdown 输出格式
**关键限制：** Markdown 表格要求每行必须在物理上是单行，不能有真正的换行符（`\n`）。

**解决方案：** 使用 HTML `<code>` + `<br>` 换行符

```python
escaped_code = html_module.escape(code_text)
code_with_br = escaped_code.replace('\n', '<br>')
parts.append(f'<br><code>{code_with_br}</code><br>')
```

**输出示例：**
```html
<br><code>apiVersion: v1<br>kind: Pod<br>metadata:<br>  name: my-pod</code><br>
```

**设计决策：**
- `<br>` 前缀：代码块与前文本间距
- `<br>` 后缀：代码块与后文本间距
- 不使用 `<pre>`：`<pre>` 中的换行符会破坏表格结构
- 不使用 ```：Markdown 表格不支持多行代码块

### 实现位置
`scripts/export.py` 第 236-342 行 `_process_table_cell()` 方法

---

## 3. Draw.io 图片支持

### 问题背景
Confluence 的 Draw.io 宏不使用 `<img>` 标签，而是将图片 URL 存储在 JavaScript 中：
```javascript
readerOpts.imageUrl = '' + '/download/attachments/487887043/image.png'
```

### 解析规则

#### 3.1 提取图片 URL
使用正则表达式匹配：
```python
drawio_pattern = r"readerOpts\.imageUrl\s*=\s*''\s*\+\s*'([^']*)'"
```

#### 3.2 嵌套位置处理
Draw.io 宏可能嵌套在不同位置：
- **顶层处理**：在 `parse_page()` 中提取所有 Draw.io 图片 URL
- **表格单元格处理**：在 `_process_table_cell()` 中处理单元格内的 Draw.io

**HTML 嵌套结构：**
```html
div → table → tbody → tr → td → div → p → drawio macro
```

#### 3.3 图片引用
```markdown
![图片](images/filename.png)
```

### 实现位置
- `scripts/export.py` 第 207-233 行（parse_page）
- `scripts/export.py` 第 280-292 行（_process_table_cell）

---

## 4. 表格单元格混合内容

### 支持的内容类型
1. **普通文本** - 直接提取
2. **图片** - `![图片](images/filename.png)`
3. **Draw.io 宏** - 同 2.3
4. **代码块** - 同 2.3

### 处理顺序
```python
# 1. 代码块（优先处理，标记为已处理）
code_blocks = cell.find_all('div', attrs={'data-macro-name': 'code'})

# 2. Draw.io 宏（检查是否已处理）
drawio_macros = cell.find_all('div', attrs={'data-macro-name': lambda x: 'drawio' in str(x).lower()})

# 3. 普通图片
imgs = cell.find_all('img')

# 4. 剩余文本（排除已处理的元素）
cell_copy = cell.__copy__()
# 移除已处理元素后提取文本
```

### 输出格式
各部分用空格连接：
```python
" ".join(str(p).strip() for p in parts if str(p).strip())
```

### 实现位置
`scripts/export.py` 第 236-342 行

---

## 5. 表格结构支持

### HTML 结构处理
Confluence 表格使用 `<thead>` 和 `<tbody>` 包装：
```html
<table>
  <thead>
    <tr>...</tr>
  </thead>
  <tbody>
    <tr>...</tr>
  </tbody>
</table>
```

### 解析规则
使用 `find_all('tr')` 查找所有行（包括 thead/tbody 内部）：
```python
for tr in element.find_all('tr'):  # 不限制 recursive
    cells = []
    for cell in tr.find_all(['th', 'td'], recursive=False):
        cell_content = self._process_table_cell(cell)
        cells.append(cell_content)
```

### Markdown 输出
```markdown
| Header 1 | Header 2 |
| --- | --- |
| Cell 1 | Cell 2 |
```

### 实现位置
`scripts/export.py` 第 349-396 行

---

## 6. 语言名称映射

### 映射表
```python
lang_map = {
    'yml': 'yaml',
    'js': 'javascript',
    'ts': 'typescript',
    'py': 'python'
}
```

### 支持的语言列表
```python
['yml', 'yaml', 'bash', 'sh', 'python', 'py', 'java',
 'javascript', 'js', 'json', 'xml', 'html', 'css', 'sql',
 'go', 'rust', 'c', 'cpp', 'typescript', 'ts']
```

---

## 7. HTML 转义

### 需要转义的字符
在 HTML 代码块中，特殊字符需要转义：
- `"` → `&quot;`
- `<` → `&lt;`
- `>` → `&gt;`
- `&` → `&amp;`

### 实现方式
```python
import html as html_module
escaped_code = html_module.escape(code_text)
```

---

## 8. 核心限制与设计决策

| 限制 | 决策 | 原因 |
|------|------|------|
| 表格单行 | 使用 `<br>` 替代换行符 | Markdown 表格不支持多行 |
| 表格代码块 | 使用 `<code>` 而非 `<pre>` | `<pre>` 中换行符破坏表格 |
| 语法高亮 | 不输出 `class="language-xxx"` | HTML `<code>` 在表格中无高亮 |
| 代码间距 | 前后加 `<br>` | 视觉分隔，提高可读性 |

---

## 9. 依赖

- `requests` - HTTP 请求
- `beautifulsoup4` - HTML 解析
- `re` - 正则表达式匹配
- `html` - HTML 转义

---

## 附录：安装与使用

### 安装 Skill

运行安装脚本自动安装到 Claude Code skills 目录：

```bash
./install.sh
```

脚本会自动：
1. 创建 `~/.claude/skills/kb-exporter/` 目录
2. 复制 `SKILL.md` 和 `scripts/export.py` 到正确位置

### 更新 Skill

修改代码后，重新运行安装脚本即可：

```bash
./install.sh
```

重启 Claude Code 使更改生效。
