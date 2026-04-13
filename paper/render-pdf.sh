#!/bin/bash
set -euo pipefail

# Render markdown with mermaid diagrams to PDF
# Usage: ./render-pdf.sh neuro-symbolic-regulated-workflows.md output.pdf

INPUT="${1:-neuro-symbolic-regulated-workflows.md}"
OUTPUT="${2:-$(basename "$INPUT" .md).pdf}"
WORK_DIR=$(mktemp -d)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Rendering $INPUT -> $OUTPUT"

# Step 1: Extract and render mermaid blocks to SVG
echo "  [1/4] Extracting mermaid diagrams..."
COUNTER=0
cp "$SCRIPT_DIR/$INPUT" "$WORK_DIR/source.md"

# Find all mermaid code blocks and render them
while IFS= read -r -d '' block; do
    COUNTER=$((COUNTER + 1))
    PNG_FILE="$WORK_DIR/mermaid-$COUNTER.png"
    echo "$block" > "$WORK_DIR/mermaid-$COUNTER.mmd"
    # Create mermaid config for black text on white
    cat > "$WORK_DIR/mermaid-config.json" << 'MERMAIDCFG'
{
  "theme": "base",
  "themeVariables": {
    "primaryColor": "#e8f5e9",
    "primaryTextColor": "#000000",
    "primaryBorderColor": "#999999",
    "secondaryColor": "#fff3e0",
    "secondaryTextColor": "#000000",
    "secondaryBorderColor": "#999999",
    "tertiaryColor": "#e1f5fe",
    "tertiaryTextColor": "#000000",
    "tertiaryBorderColor": "#999999",
    "lineColor": "#333333",
    "textColor": "#000000",
    "mainBkg": "#ffffff",
    "nodeBorder": "#999999",
    "clusterBkg": "#f5f5f5",
    "titleColor": "#000000",
    "edgeLabelBackground": "#ffffff",
    "nodeTextColor": "#000000"
  }
}
MERMAIDCFG
    # Render as PNG (WeasyPrint can't handle foreignObject in SVGs)
    PNG_FILE="$WORK_DIR/mermaid-$COUNTER.png"
    pnpm --silent dlx @mermaid-js/mermaid-cli -i "$WORK_DIR/mermaid-$COUNTER.mmd" -o "$PNG_FILE" -b white -c "$WORK_DIR/mermaid-config.json" -s 3 --quiet 2>/dev/null
    echo "    Rendered diagram $COUNTER"
done < <(python3 -c "
import re, sys
content = open('$WORK_DIR/source.md').read()
blocks = re.findall(r'\`\`\`mermaid\n(.*?)\`\`\`', content, re.DOTALL)
for b in blocks:
    sys.stdout.write(b)
    sys.stdout.write('\0')
")

# Step 2: Replace mermaid blocks with SVG image references
echo "  [2/4] Replacing mermaid blocks with rendered SVGs..."
python3 -c "
import re

with open('$WORK_DIR/source.md', 'r') as f:
    content = f.read()

counter = 0
def replace_mermaid(match):
    global counter
    counter += 1
    svg_path = '$WORK_DIR/mermaid-' + str(counter) + '.png'
    return f'![Diagram {counter}]({svg_path})'

content = re.sub(r'\`\`\`mermaid\n.*?\`\`\`', replace_mermaid, content, flags=re.DOTALL)

with open('$WORK_DIR/processed.md', 'w') as f:
    f.write(content)
"

# Step 3: Convert to HTML with pandoc
echo "  [3/4] Converting markdown to HTML..."
pandoc "$WORK_DIR/processed.md" \
    -o "$WORK_DIR/output.html" \
    --standalone \
    --embed-resources \
    --self-contained \
    2>/dev/null || pandoc "$WORK_DIR/processed.md" \
    -o "$WORK_DIR/output.html" \
    --standalone

# Inject clean CSS directly into the HTML
python3 -c "
html = open('$WORK_DIR/output.html').read()
css = '''
<style>
  body {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.5;
    max-width: 800px;
    margin: 0 auto;
    padding: 40px;
    color: #1a1a1a;
  }
  h1 { font-size: 20pt; margin-top: 2em; border-bottom: 1px solid #ddd; padding-bottom: 0.3em; }
  h2 { font-size: 15pt; margin-top: 1.5em; }
  h3 { font-size: 12pt; margin-top: 1.2em; }
  table { border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 10pt; table-layout: auto; word-wrap: break-word; }
  th, td { border: 1px solid #ccc; padding: 6px 10px; text-align: left; white-space: normal; }
  th { background: #f5f5f5; font-weight: 600; }
  /* Center-align numeric/score columns — keep compact */
  td[align="center"], th[align="center"] { text-align: center; white-space: nowrap; }
  code { font-family: 'SF Mono', Menlo, monospace; font-size: 9pt; background: #f5f5f5; padding: 1px 4px; border-radius: 3px; }
  pre { background: #f5f5f5; padding: 12px; border-radius: 4px; overflow-x: auto; }
  pre code { background: none; padding: 0; }
  img { max-width: 100%; height: auto; margin: 1em 0; }
  blockquote { border-left: 3px solid #ddd; margin-left: 0; padding-left: 1em; color: #555; }
  hr { border: none; border-top: 1px solid #ddd; margin: 2em 0; }
  strong { font-weight: 600; }
  .title-block { text-align: center; margin-bottom: 2em; }
  @page { margin: 2.5cm; size: A4; }
  @media print { body { max-width: none; padding: 0; } }
</style>
'''
html = html.replace('</head>', css + '</head>')
open('$WORK_DIR/output.html').close()
with open('$WORK_DIR/output.html', 'w') as f:
    f.write(html)
"

# Step 4: Convert HTML to PDF with weasyprint
echo "  [4/4] Rendering PDF..."
weasyprint "$WORK_DIR/output.html" "$SCRIPT_DIR/$OUTPUT" 2>/dev/null

echo "Done: $OUTPUT"
echo "  Location: $SCRIPT_DIR/$OUTPUT"

# Cleanup
rm -rf "$WORK_DIR"
