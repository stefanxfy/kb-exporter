---
name: kb-exporter
description: Export KB (kb.cvte.com) pages to Markdown with images. Automatically detects kb.cvte.com URLs and asks if user wants to export. Supports batch export of multiple URLs. Downloads images locally and fixes image references. Uses article title as filename (parsed from h1 or page title). Extracts content from main-content wiki-content div. Requires JSESSIONID cookie for authentication.
---

# KB Exporter

Export KB knowledge base pages to Markdown format with local images.

## When to Use

- User shares a kb.cvte.com URL
- User wants to export KB articles to Markdown
- User needs to batch export multiple KB pages
- User wants to save KB content with images for offline use

## Workflow

When a kb.cvte.com URL is detected:

1. **Ask user**: "检测到 KB 链接，是否要导出为 Markdown 文档？"
2. **Check cookie**: If user confirms, check if `~/.kb_cache/cookies.json` exists
3. **Validate cookie**: Try to fetch page with existing cookie
4. **Handle expired cookie**:
   - If cookie expired/invalid: "Cookie 已过期，请提供新的 JSESSIONID"
   - Parse user input (e.g., `JSESSIONID=ABC123` or just `ABC123`)
   - Auto-save to `~/.kb_cache/cookies.json`
5. **Export**: Download page content and images to current working directory
6. **Save**: Create `{title}/{title}.md` with images in `{title}/images/`

**Important**: Default output is the current working directory (where Claude Code is running), NOT the kb-exporter project directory.

## Quick Start

**Single URL export:**
```bash
python scripts/export.py "https://kb.cvte.com/pages/viewpage.action?pageId=123456"
```

**Batch export:**
```bash
python scripts/export.py url1 url2 url3 -o ./output
```

## Authentication

**Required Cookie:** Only `JSESSIONID` is required.

**Cookie file location:** `~/.kb_cache/cookies.json`

**Format:**
```json
{
  "JSESSIONID": "F43652A092599235036F2B0E828C8FBA"
}
```

**Getting JSESSIONID from browser:**

1. Login to kb.cvte.com
2. Open DevTools (F12) → Application/Storage → Cookies
3. Find `JSESSIONID` value
4. Copy the value

Or use browser extension "Get cookies.txt LOCALLY" and extract JSESSIONID.

## Script Usage

```bash
python scripts/export.py <urls> [options]
```

**Options:**
- `-o, --output DIR` - Output directory (default: current directory)
- `--no-images` - Skip downloading images
- `-c, --cookie-file PATH` - Custom cookie file path

**Examples:**

```bash
# Single page with images
python scripts/export.py https://kb.cvte.com/pages/viewpage.action?pageId=495126015

# Multiple pages to specific folder
python scripts/export.py url1 url2 -o ./docs

# Export without images
python scripts/export.py <url> --no-images
```

## Output Format

**Default location:** Current working directory (where Claude Code is running)

**Directory structure:**
```
{文章标题}/
├── {文章标题}.md       # Markdown 文档
└── images/            # 图片目录
    ├── image1.png
    └── image2.png
```

**Frontmatter included:**
```yaml
---
title: Article Title
source: https://kb.cvte.com/pages/viewpage.action?pageId=123456
page_id: 123456
images: 5
---
```

**Image references:** `![图片](images/filename.png)`

## Content Extraction

- **Content area:** `<div id="main-content" class="wiki-content">`
- **Title source:** First `<h1>` tag (cleaned of `id-\d+` prefix)
- **Images:** Downloaded to `./images/` subdirectory
- **Supported elements:** Headers, paragraphs, lists, code blocks, links, images

## Troubleshooting

**"Login required" error:**
- Cookies have expired - re-export from browser and update `cookies.json`

**Missing images:**
- Check network connectivity
- Verify cookies are valid
- Run with `--no-images` to skip

**"Could not find content area":**
- Page structure may be different
- Open an issue with the page URL
