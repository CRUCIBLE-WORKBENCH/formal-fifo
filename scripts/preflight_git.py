#!/usr/bin/env python3
"""Audit this demo's indexed and unignored files without changing Git state."""
from pathlib import Path
import ast
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args]).decode('utf-8')


assert Path(git('rev-parse', '--show-toplevel').strip()).resolve() == ROOT
entries = git('ls-files', '--stage', '-z').split('\0')
indexed = {}
for item in filter(None, entries):
    meta, path = item.split('\t', 1)
    mode, digest, stage = meta.split()
    assert stage == '0' and mode in ('100644', '100755'), 'Unexpected Git mode: ' + path
    indexed[path] = (mode, digest)
paths = sorted(set(indexed) | set(filter(None, git('ls-files', '--others', '--exclude-standard', '-z').split('\0'))))
assert paths, 'No candidate files'
allowed_roots = {'Makefile', '.gitignore', '.gitattributes', 'README.md', 'crucible.toml', 'crucible.lock', 'requirements.txt', 'docs', 'evidence', 'config', 'scripts', 'layout', 'spice', 'rtl', 'tests', 'src', 'reference', 'formal'}
for path in paths:
    p = ROOT / path
    assert p.is_file() and not p.is_symlink(), 'Missing or linked candidate: ' + path
    assert Path(path).parts[0] in allowed_roots, 'Unexpected candidate root: ' + path
    assert not re.search(r'(?i)(^|/)(?:AGENTS\.md|SKILL\.md|GATES\.md|WORKLOG\.md|local\.env\.sh|\.env(?:\..*)?|\.git|\.unlazy|\.claude|\.codex|__pycache__)(/|$)', path), 'Private/local candidate: ' + path
    assert p.suffix.lower() not in {'.so', '.dll', '.exe', '.odb', '.def', '.spef', '.gds', '.gdsii', '.pyc', '.vvp', '.zip', '.gz', '.token', '.key', '.pem'}, 'Generated/runtime candidate: ' + path
    assert p.stat().st_size <= 5 * 1024 * 1024, 'Oversize candidate: ' + path
    data = p.read_bytes()
    if p.suffix.lower() in ('.pdf', '.pptx'):
        continue
    text = data.decode('utf-8')
    assert not re.search(r'(?i)([a-z]:[\\/]Users[\\/]|/mnt/[a-z]/Users/|/home/(?!you/|user/)[a-z0-9_-]+/)', text), 'Personal absolute path: ' + path
    assert not re.search(r'(?:ghp_[A-Za-z0-9]{30,}|glpat-[A-Za-z0-9_-]{16,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|https?://[^\s/@:]+:[^\s/@]+@)', text), 'Possible credential: ' + path
    if p.suffix == '.sh':
        assert b'\r' not in data and not data.startswith(b'\xef\xbb\xbf'), 'Shell encoding/endings: ' + path
        if path in indexed:
            assert indexed[path][0] == '100755', 'Shell file lacks executable index mode: ' + path
    if p.suffix == '.py':
        ast.parse(text, filename=path)
    if p.suffix == '.md':
        for target in re.findall(r'\]\(([^)]+)\)', text):
            if re.match(r'\w+://|mailto:|#', target):
                continue
            relative = target.split('#', 1)[0].split(' "', 1)[0]
            assert (p.parent / relative).is_file(), 'Broken Markdown link: ' + path + ' -> ' + relative
manifest = json.loads((ROOT / 'evidence/documents.sha256.json').read_text())
for path, expected in manifest.items():
    assert path in paths and hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, 'Whitepaper identity mismatch: ' + path
for args in (('diff', '--check'), ('diff', '--cached', '--check')):
    subprocess.run(['git', '-C', str(ROOT), *args], check=True)
print(f'GIT_PREFLIGHT_PASS files={len(paths)} indexed={len(indexed)} documents={len(manifest)}')
