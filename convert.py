#!/usr/bin/env python3
"""
convert.py — Convert Obsidian microeconomics vault notes to Quarto .qmd files.
Run from the grad-micro-notes/ directory: python convert.py
"""

import re
import os
from pathlib import Path

VAULT_DIR = Path("/Users/andreabusolo/Desktop/Università/Obsidian/Andrea/Microeconomics")
OUTPUT_DIR = Path("/Users/andreabusolo/Documents/GitHub/grad-micro-notes")

# Obsidian callout type -> (quarto callout type, collapse)
CALLOUT_MAP = {
    "definition":  ("note",      False),
    "theorem":     ("important", False),
    "proposition": ("important", False),
    "proof":       ("tip",       True),
    "remark":      ("caution",   False),
    "example":     ("note",      False),
    "lemma":       ("warning",   False),
    "corollary":   ("warning",   False),
    "claim":       ("warning",   False),
}

def strip_yaml(content):
    """Remove YAML frontmatter block entirely (tags/aliases not needed in Quarto)."""
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            return content[end + 4:].lstrip("\n")
    return content

def extract_title(content):
    """Extract the first H1 heading as the page title."""
    match = re.search(r'^# (.+)$', content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return "Untitled"

def convert_callouts(content):
    """Convert Obsidian > [!type] callout blocks to Quarto ::: {.callout-type} divs."""
    lines = content.split('\n')
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Match callout header: > [!type] Optional Title
        match = re.match(r'^> \[!(\w+)\](.*?)$', line)
        if match:
            callout_type_raw = match.group(1).lower()
            title_text = match.group(2).strip()
            quarto_type, collapse = CALLOUT_MAP.get(callout_type_raw, ("note", False))

            # Collect all continuation lines starting with >
            callout_body = []
            i += 1
            while i < len(lines):
                l = lines[i]
                if l.startswith('> '):
                    callout_body.append(l[2:])
                    i += 1
                elif l == '>':
                    callout_body.append('')
                    i += 1
                else:
                    break

            # Build Quarto fenced div
            collapse_attr = ' collapse="true"' if collapse else ''
            if callout_type_raw == "example":
                result.append(f'::: {{.callout-{quarto_type} icon=false appearance="simple"{collapse_attr}}}')
            else:
                result.append(f'::: {{.callout-{quarto_type} icon=false{collapse_attr}}}')

            # Title line
            display_type = callout_type_raw.capitalize()
            if title_text:
                result.append(f'## {title_text}')
            else:
                result.append(f'## {display_type}')

            result.extend(callout_body)
            result.append(':::')
            result.append('')
        else:
            result.append(line)
            i += 1
    return '\n'.join(result)

def convert_wikilinks(content, source_path):
    """Convert [[wikilinks]] to relative .qmd links."""
    source_dir = source_path.parent

    def replace(match):
        raw = match.group(1).strip()
        # Strip display text if present: [[target|display]]
        if '|' in raw:
            target, display = raw.split('|', 1)
        else:
            target = raw
            display = raw.split('/')[-1].replace('_', ' ')

        target = target.strip()

        # Determine relative path
        if '/' in target:
            # Cross-directory link e.g. Part_II_Consumer_Theory/2.1_Preference_Relations
            parts = target.split('/')
            rel = '../' + '/'.join(parts) + '.qmd'
        else:
            # Same-directory link (could be Index -> index)
            if target == 'Index':
                target = 'index'
            rel = target + '.qmd'

        return f'[{display}]({rel})'

    return re.sub(r'\[\[([^\]]+)\]\]', replace, content)

def add_yaml_title(content, title):
    """Prepend minimal Quarto YAML with title."""
    safe_title = title.replace('"', '\\"')
    yaml = f'---\ntitle: "{safe_title}"\n---\n\n'
    return yaml + content

def process_file(md_path: Path, out_path: Path):
    """Full conversion pipeline for one file."""
    raw = md_path.read_text(encoding='utf-8')
    content = strip_yaml(raw)
    title = extract_title(content)
    content = convert_callouts(content)
    content = convert_wikilinks(content, out_path)
    content = add_yaml_title(content, title)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding='utf-8')
    print(f"  ✓  {out_path.relative_to(OUTPUT_DIR)}")

def get_output_name(md_path: Path) -> str:
    """Map source filename to output .qmd filename."""
    name = md_path.stem
    if name == '00_Program_Overview':
        return 'index'
    if name == 'Index':
        return 'index'
    return name

def main():
    print(f"Converting notes from:\n  {VAULT_DIR}\nto:\n  {OUTPUT_DIR}\n")
    converted = 0
    skipped = 0
    for md_path in sorted(VAULT_DIR.rglob('*.md')):
        # Skip Templates folder
        if 'Templates' in md_path.parts:
            skipped += 1
            continue
        # Compute relative path
        rel = md_path.relative_to(VAULT_DIR)
        parts = list(rel.parts)
        # Replace filename
        parts[-1] = get_output_name(md_path) + '.qmd'
        # Handle root-level files
        if len(parts) == 1:
            out_path = OUTPUT_DIR / parts[0]
        else:
            out_path = OUTPUT_DIR / Path(*parts)
        process_file(md_path, out_path)
        converted += 1
    print(f"\nDone. Converted: {converted}, Skipped (Templates): {skipped}")

if __name__ == '__main__':
    main()
