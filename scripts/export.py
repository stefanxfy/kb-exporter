#!/usr/bin/env python3
"""
KB to Markdown Exporter
Exports KB pages to Markdown with images
"""

import sys
import os
import json
import re
import argparse
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: Required packages not installed.")
    print("Install with: pip install requests beautifulsoup4")
    sys.exit(1)


class KBExporter:
    """Export KB pages to Markdown"""

    def __init__(self, cookie_file=None):
        self.cookie_file = cookie_file or Path.home() / ".kb_cache" / "cookies.json"
        self.session = requests.Session()
        self.jsessionid = None
        self._load_cookies()

    def _load_cookies(self):
        """Load JSESSIONID from file"""
        if Path(self.cookie_file).exists():
            with open(self.cookie_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle different formats
            if isinstance(data, dict):
                self.jsessionid = data.get('JSESSIONID')
            elif isinstance(data, list):
                for cookie in data:
                    name = cookie.get('name', cookie.get('key', ''))
                    if name == 'JSESSIONID':
                        self.jsessionid = cookie.get('value')
                        break

            if self.jsessionid:
                self.session.cookies.set('JSESSIONID', self.jsessionid)
                return True
        return False

    def _save_cookie(self, jsessionid):
        """Save JSESSIONID to file"""
        # Ensure directory exists
        Path(self.cookie_file).parent.mkdir(parents=True, exist_ok=True)

        with open(self.cookie_file, 'w', encoding='utf-8') as f:
            json.dump({"JSESSIONID": jsessionid}, f, indent=2)

        self.jsessionid = jsessionid
        self.session.cookies.set('JSESSIONID', jsessionid)
        return True

    def check_login(self, url_or_page_id=None):
        """Check if current cookie is valid by trying to fetch a page"""
        if not self.jsessionid:
            return False, "No cookie found"

        # Use a simple test URL or provided URL
        test_url = url_or_page_id
        if not test_url:
            test_url = "https://kb.cvte.com/"

        try:
            response = self.session.get(test_url, timeout=10, allow_redirects=True)

            # Check if redirected to login page
            if 'login' in response.url or 'home.cvte.com' in response.url:
                return False, "Cookie expired"

            # Check if we can access a KB page
            if response.status_code == 200:
                return True, "Cookie valid"

            return False, f"Unexpected status: {response.status_code}"

        except requests.RequestException as e:
            return False, f"Network error: {e}"

    def parse_cookie_input(self, user_input):
        """Parse user input to extract JSESSIONID value

        Supports formats:
        - JSESSIONID=ABC123
        - ABC123
        - {"JSESSIONID": "ABC123"}
        """
        user_input = user_input.strip()

        # JSON format
        if user_input.startswith('{'):
            try:
                data = json.loads(user_input)
                return data.get('JSESSIONID')
            except json.JSONDecodeError:
                pass

        # KEY=VALUE format
        if '=' in user_input and not user_input.startswith('http'):
            key, value = user_input.split('=', 1)
            if 'JSESSIONID' in key.upper() or 'SESSIONID' in key.upper():
                return value.strip()

        # Just the value (32 char hex-like string)
        if re.match(r'^[A-F0-9]{32,}$', user_input.upper()):
            return user_input

        # Try to find JSESSIONID in the input
        match = re.search(r'JSESSIONID[=:]\s*([A-F0-9]{32,})', user_input, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    def extract_page_id(self, url):
        """Extract page ID from URL"""
        patterns = [
            r'[?&]pageId=(\d+)',
            r'/pages/(\d+)',
            r'/viewpage\.action\?pageId=(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def fetch_page(self, page_id):
        """Fetch page content"""
        url = f"https://kb.cvte.com/pages/viewpage.action?pageId={page_id}"
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response.text, response.url

    def get_image_filename(self, img_element):
        """Extract filename from img element"""
        src = img_element.get('src', '')
        if '/download/attachments/' in src:
            return src.split('/')[-1].split('?')[0]
        return None

    def download_image(self, url, output_dir):
        """Download single image"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            filename = url.split('/')[-1].split('?')[0]
            filepath = Path(output_dir) / filename
            with open(filepath, 'wb') as f:
                f.write(response.content)
            return filename, len(response.content)
        except Exception as e:
            print(f"  Warning: Failed to download {url}: {e}")
            return None, 0

    def parse_page(self, html):
        """Parse page and extract title, content, images"""
        soup = BeautifulSoup(html, 'html.parser')

        # Extract title
        title = "Untitled"
        title_elem = soup.find('h1')
        if title_elem:
            title_text = title_elem.get_text(strip=True)
            title = re.sub(r'^id-\d+\s*', '', title_text)
        else:
            title_elem = soup.find('title')
            if title_elem:
                title = title_elem.get_text(strip=True).split(' - ')[0]

        # Find content area
        content_div = soup.find('div', {'id': 'main-content', 'class': 'wiki-content'})
        if not content_div:
            content_div = soup.find('div', {'id': 'main-content'})
        if not content_div:
            content_div = soup.find('div', class_='wiki-content')

        # Extract images
        images = []
        if content_div:
            # Method 1: Find <img> tags
            for img in content_div.find_all('img'):
                src = img.get('src', '')
                if '/download/attachments/' in src:
                    filename = self.get_image_filename(img)
                    if filename:
                        if src.startswith('/'):
                            full_url = f"https://kb.cvte.com{src}"
                        else:
                            full_url = src
                        images.append({
                            'filename': filename,
                            'url': full_url.split('?')[0]
                        })

            # Method 2: Find draw.io macro images from JavaScript
            # Draw.io macros store image URLs in script tags with readerOpts.imageUrl variable
            html_str = str(content_div)
            # Pattern to match: readerOpts.imageUrl = '' + '/download/attachments/...'
            drawio_pattern = r"readerOpts\.imageUrl\s*=\s*''\s*\+\s*'([^']*)'"
            for match in re.finditer(drawio_pattern, html_str):
                img_url = match.group(1)
                # Extract filename from URL
                if '/download/attachments/' in img_url:
                    # URL decode and extract filename
                    from urllib.parse import unquote
                    decoded_url = unquote(img_url)
                    filename = decoded_url.split('/')[-1].split('?')[0]
                    if filename:
                        if img_url.startswith('/'):
                            full_url = f"https://kb.cvte.com{img_url}"
                        else:
                            full_url = img_url
                        # Remove query parameters for the download URL
                        clean_url = full_url.split('?')[0] if '?' in img_url else full_url
                        # Avoid duplicates
                        if not any(img['filename'] == filename for img in images):
                            images.append({
                                'filename': filename,
                                'url': clean_url
                            })

        return title, content_div, images

    def _process_table_cell(self, cell, image_prefix="images/"):
        """Process table cell content - handle text, images, and draw.io macros"""
        parts = []

        # Check for draw.io macros first (before processing anything else)
        drawio_macros = cell.find_all('div', attrs={'data-macro-name': lambda x: x and 'drawio' in str(x).lower()})
        if drawio_macros:
            for macro in drawio_macros:
                from urllib.parse import unquote
                html_str = str(macro)
                drawio_pattern = r"readerOpts\.imageUrl\s*=\s*''\s*\+\s*'([^']*)'"
                matches = list(re.finditer(drawio_pattern, html_str))
                for match in matches:
                    img_url = match.group(1)
                    decoded_url = unquote(img_url)
                    filename = decoded_url.split('/')[-1].split('?')[0]
                    parts.append(f"![图片]({image_prefix}{filename})")

        # Check for regular images
        imgs = cell.find_all('img')
        if imgs:
            for img in imgs:
                filename = self.get_image_filename(img)
                if filename:
                    parts.append(f"![图片]({image_prefix}{filename})")

        # Get text content (excluding images)
        # Create a copy to modify
        cell_copy = cell.__copy__()
        # Remove images from the copy
        for img in cell_copy.find_all('img'):
            img.decompose()
        # Remove drawio divs from the copy
        for div in cell_copy.find_all('div', attrs={'data-macro-name': lambda x: x and 'drawio' in str(x).lower()}):
            div.decompose()
        # Get remaining text
        text = cell_copy.get_text(strip=True)
        if text:
            parts.append(text)

        # If no content, return empty string
        if not parts:
            return ""

        # Join parts - if both text and images, put text first
        return " ".join(parts)

    def process_element(self, element, image_prefix="images/"):
        """Convert HTML element to Markdown"""
        if not element or not hasattr(element, 'name'):
            return ""

        tag = element.name

        # Check for draw.io macro before other processing
        macro_name = element.get('data-macro-name', '')
        if macro_name and 'drawio' in macro_name.lower():
            # Extract image URL from draw.io macro JavaScript
            from urllib.parse import unquote
            html_str = str(element)
            drawio_pattern = r"readerOpts\.imageUrl\s*=\s*''\s*\+\s*'([^']*)'"
            matches = list(re.finditer(drawio_pattern, html_str))
            if matches:
                # Generate markdown for each image found
                result = ""
                for match in matches:
                    img_url = match.group(1)
                    decoded_url = unquote(img_url)
                    filename = decoded_url.split('/')[-1].split('?')[0]
                    result += f"\n![图片]({image_prefix}{filename})\n"
                return result

        # Confluence code block - handle before other elements
        classes = element.get('class', [])
        if isinstance(classes, list):
            class_str = ' '.join(classes)
        else:
            class_str = str(classes) if classes else ''

        if 'code' in class_str and 'panel' in class_str:
            # This is a Confluence code block
            # Find the code content div
            code_content = element.find('div', class_='codeContent')
            if code_content:
                # Try to find filename from header
                header = element.find('div', class_='codeHeader')
                filename = None
                if header:
                    filename_elem = header.find('b')
                    if filename_elem:
                        filename = filename_elem.get_text(strip=True)

                # Extract code text - preserve formatting
                code_text = code_content.get_text('\n')
                result = f"\n```{filename or 'bash'}\n{code_text}\n```\n\n"
                return result

        # Standard pre/code block
        if tag == 'pre':
            code_text = element.get_text()
            return f"\n```\n{code_text}\n```\n"

        # Headers
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = tag[1]
            text = element.get_text(strip=True)
            text = re.sub(r'^id-\d+\s*', '', text)
            if text:
                return f"\n{'#' * int(level)} {text}\n"

        # Blockquote
        if tag == 'blockquote':
            text = element.get_text(strip=True)
            return f"> {text}\n"

        # Unordered list
        if tag == 'ul':
            lines = []
            for li in element.find_all('li', recursive=False):
                text = li.get_text(strip=True)
                if text:
                    lines.append(f"- {text}")
            return '\n'.join(lines) + '\n\n'

        # Ordered list
        if tag == 'ol':
            lines = []
            for i, li in enumerate(element.find_all('li', recursive=False), 1):
                text = li.get_text(strip=True)
                if text:
                    lines.append(f"{i}. {text}")
            return '\n'.join(lines) + '\n\n'

        # Table
        if tag == 'table':
            rows = []
            # Find all rows (including inside thead/tbody)
            for tr in element.find_all('tr'):
                cells = []
                # Get all cells (th or td)
                for cell in tr.find_all(['th', 'td'], recursive=False):
                    # Process cell content - handle text and images
                    cell_content = self._process_table_cell(cell, image_prefix)
                    cells.append(cell_content)
                if cells:
                    rows.append(cells)

            if not rows:
                return ""

            # Build markdown table
            result = []
            # Header row
            result.append('| ' + ' | '.join(rows[0]) + ' |')
            # Separator row
            result.append('| ' + ' | '.join(['---'] * len(rows[0])) + ' |')
            # Data rows
            for row in rows[1:]:
                result.append('| ' + ' | '.join(row) + ' |')

            return '\n'.join(result) + '\n\n'

        # Table wrapper div - try to extract table from it
        if tag == 'div' and 'table-wrap' in class_str:
            table = element.find('table')
            if table:
                return self.process_element(table, image_prefix)

        # Paragraph
        if tag == 'p':
            result = ""

            # Check for draw.io macros first
            drawio_macros = element.find_all('div', attrs={'data-macro-name': lambda x: x and 'drawio' in str(x).lower()})
            if drawio_macros:
                # Process draw.io macros
                for macro in drawio_macros:
                    from urllib.parse import unquote
                    html_str = str(macro)
                    drawio_pattern = r"readerOpts\.imageUrl\s*=\s*''\s*\+\s*'([^']*)'"
                    matches = list(re.finditer(drawio_pattern, html_str))
                    for match in matches:
                        img_url = match.group(1)
                        decoded_url = unquote(img_url)
                        filename = decoded_url.split('/')[-1].split('?')[0]
                        result += f"\n![图片]({image_prefix}{filename})\n"

            # Check for regular images
            imgs = element.find_all('img')
            text_content = element.get_text(strip=True)

            # Pure image paragraph (no draw.io, only regular images)
            if not drawio_macros and imgs and not text_content:
                for img in imgs:
                    filename = self.get_image_filename(img)
                    if filename:
                        result += f"\n![图片]({image_prefix}{filename})\n"
                return result

            # Mixed content
            for child in element.children:
                if hasattr(child, 'name'):
                    if child.name == 'img':
                        filename = self.get_image_filename(child)
                        if filename:
                            result += f"![图片]({image_prefix}{filename})"
                    elif child.name == 'a' and child.get('href'):
                        text = child.get_text(strip=True)
                        href = child['href']
                        result += f"[{text}]({href})"
                    elif child.name in ['strong', 'b']:
                        result += f"**{child.get_text()}**"
                    elif child.name in ['em', 'i']:
                        result += f"*{child.get_text()}*"
                    elif child.name == 'code':
                        result += f"`{child.get_text()}`"
                    elif child.name == 'br':
                        result += "\n"
                    else:
                        if child.string:
                            result += child.string
                else:
                    if str(child).strip():
                        result += str(child).strip()

            # Return result if there's any content (including draw.io images)
            if result.strip():
                return result + "\n"

        # Standalone image
        if tag == 'img':
            filename = self.get_image_filename(element)
            if filename:
                return f"\n![图片]({image_prefix}{filename})\n"

        return ""

    def to_markdown(self, content_div):
        """Convert content div to Markdown"""
        if not content_div:
            return ""

        markdown_lines = []
        for element in content_div.children:
            if hasattr(element, 'name') and element.name:
                md = self.process_element(element)
                if md:
                    markdown_lines.append(md)

        return '\n'.join(markdown_lines)

    def sanitize_filename(self, title):
        """Sanitize title for use as filename"""
        title = re.sub(r'[<>:"/\\|?*]', '', title)
        title = re.sub(r'[\s\u3000]+', '-', title)
        return title[:100] or 'untitled'

    def export(self, url, output_dir=".", download_images=True):
        """Export a single page"""
        print(f"\n{'='*50}")
        print(f"Exporting: {url}")
        print(f"{'='*50}")

        # Extract page ID
        page_id = self.extract_page_id(url)
        if not page_id:
            print(f"Error: Could not extract page ID from URL: {url}")
            return None

        print(f"Page ID: {page_id}")

        # Check cookie first
        if not self.jsessionid:
            print("Error: No JSESSIONID found. Please set up cookie first.")
            return None

        # Fetch page
        print("Fetching page...")
        try:
            response = self.session.get(f"https://kb.cvte.com/pages/viewpage.action?pageId={page_id}", timeout=30)
            response.raise_for_status()
            html = response.text
            final_url = response.url
        except Exception as e:
            print(f"Error fetching page: {e}")
            return None

        # Check if login required
        if 'login' in final_url or 'home.cvte.com' in final_url:
            print("Error: Login required. JSESSIONID has expired.")
            print("Please update your cookie in ~/.kb_cache/cookies.json")
            return None

        # Parse page
        print("Parsing page...")
        title, content_div, images = self.parse_page(html)

        if not content_div:
            print("Error: Could not find content area")
            return None

        print(f"Title: {title}")
        print(f"Images found: {len(images)}")

        # Sanitize title for directory name
        safe_title = self.sanitize_filename(title)

        # Create article directory
        article_dir = Path(output_dir) / safe_title
        article_dir.mkdir(parents=True, exist_ok=True)

        # Download images
        image_dir = article_dir / "images"
        downloaded = []
        if download_images and images:
            image_dir.mkdir(exist_ok=True)
            print(f"\nDownloading {len(images)} images...")
            for i, img_info in enumerate(images, 1):
                filename, size = self.download_image(img_info['url'], image_dir)
                if filename:
                    downloaded.append(filename)
                    print(f"  [{i}/{len(images)}] {filename} ({size} bytes)")

        # Convert to Markdown
        print("\nConverting to Markdown...")
        markdown = self.to_markdown(content_div)

        # Add frontmatter
        frontmatter = f"""---
title: {title}
source: {url}
page_id: {page_id}
images: {len(downloaded)}
---

"""
        markdown = frontmatter + markdown

        # Save file
        filepath = article_dir / f"{safe_title}.md"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown)

        print(f"\n✓ Exported to: {filepath}")
        print(f"  Title: {title}")
        print(f"  Images: {len(downloaded)}")

        return filepath


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Export KB pages to Markdown',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export single page
  python export.py https://kb.cvte.com/pages/viewpage.action?pageId=495126015

  # Export multiple pages
  python export.py url1 url2 url3

  # Export to specific directory
  python export.py https://kb.cvte.com/pages/viewpage.action?pageId=495126015 -o ./output

  # Skip image download
  python export.py <url> --no-images

  # Set/update JSESSIONID
  python export.py --cookie "JSESSIONID=ABC123..."
        """
    )
    parser.add_argument('urls', nargs='*', help='KB page URLs')
    parser.add_argument('-o', '--output', default='.', help='Output directory')
    parser.add_argument('--no-images', action='store_true', help='Skip downloading images')
    parser.add_argument('-c', '--cookie', help='Set JSESSIONID cookie (format: JSESSIONID=value or just value)')
    parser.add_argument('--check-cookie', action='store_true', help='Check if current cookie is valid')

    args = parser.parse_args()

    # Create exporter
    exporter = KBExporter()

    # Handle cookie operations
    if args.cookie:
        jsessionid = exporter.parse_cookie_input(args.cookie)
        if jsessionid:
            exporter._save_cookie(jsessionid)
            print(f"✓ JSESSIONID saved to {exporter.cookie_file}")
            valid, msg = exporter.check_login()
            if valid:
                print(f"✓ {msg}")
            else:
                print(f"⚠ {msg}")
            return
        else:
            print("Error: Could not parse JSESSIONID from input")
            print("Expected format: JSESSIONID=ABC123 or just ABC123")
            return

    if args.check_cookie:
        if not exporter.jsessionid:
            print("No JSESSIONID found. Set one with --cookie")
        else:
            valid, msg = exporter.check_login()
            print(f"Cookie status: {msg}")
        return

    # Require URLs for export
    if not args.urls:
        parser.print_help()
        print("\nError: No URLs provided")
        return

    if not exporter.jsessionid:
        print("Error: No JSESSIONID found.")
        print(f"Please set up cookie in {exporter.cookie_file}")
        print("Or use: python export.py --cookie JSESSIONID=your_value")
        return

    # Export each URL
    results = []
    for url in args.urls:
        result = exporter.export(url, output_dir=args.output, download_images=not args.no_images)
        results.append((url, result))

    # Summary
    print(f"\n{'='*50}")
    print("Export Summary")
    print(f"{'='*50}")
    for url, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {url}")

    success = sum(1 for _, r in results if r)
    print(f"\nTotal: {success}/{len(results)} exported successfully")


if __name__ == "__main__":
    main()
