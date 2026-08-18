#!/usr/bin/env python3
"""博客管理脚本 — Hugo + GitHub Pages"""
import os, sys, json, base64, re
from urllib.request import Request, urlopen
from urllib.error import HTTPError

TOKEN = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN') or ''
REPO = os.environ.get('GH_REPO') or 'Ilyfalt/Ilyfalt.github.io'
DIR = 'content/posts'
BRANCH = 'main'
API = 'https://api.github.com'

def gh(method, path, data=None):
    body = json.dumps(data).encode() if data else None
    req = Request(API + path, data=body, method=method)
    req.add_header('Authorization', 'Bearer ' + TOKEN)
    req.add_header('Accept', 'application/vnd.github+json')
    if body: req.add_header('Content-Type', 'application/json')
    try:
        with urlopen(req) as r:
            return json.loads(r.read()) if r.status != 204 else None
    except HTTPError as e:
        msg = json.loads(e.read()).get('message', str(e)) if e.code != 204 else str(e)
        raise SystemExit(f'❌ {msg}')

def b64e(s): return base64.b64encode(s.encode()).decode()
def b64d(s): return base64.b64decode(s).decode()
def ep(p): return '/'.join(urllib_quote(x) for x in p.split('/'))

def urllib_quote(s):
    import urllib.parse
    return urllib.parse.quote(s, safe='')

def list_posts():
    try:
        items = gh('GET', f'/repos/{REPO}/contents/{DIR}')
        if not isinstance(items, list): return []
        posts = []
        for f in items:
            if not f['name'].endswith('.md'): continue
            try:
                d = gh('GET', f'/repos/{REPO}/contents/{DIR}/{ep(f["name"])}')
                md = b64d(d['content'])
                is_draft = bool(re.search(r'^---[\s\S]*?draft:\s*true[\s\S]*?---', md))
                posts.append((f['name'], '📄' if not is_draft else '📝草稿'))
            except:
                posts.append((f['name'], '❓'))
        return posts
    except Exception as e:
        raise SystemExit(f'❌ 列表失败: {e}')

def publish(filepath):
    if not os.path.isfile(filepath):
        raise SystemExit(f'❌ 文件不存在: {filepath}')
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    # 解析或生成 front matter
    has_fm = re.match(r'^---\s*\n', content)
    if not has_fm:
        # 从文件名取标题
        title = os.path.splitext(os.path.basename(filepath))[0]
        today = __import__('datetime').date.today().isoformat()
        fm = f'---\ntitle: {title}\ndate: {today}\ndraft: false\n---\n\n'
        content = fm + content
    # 确定文件名
    m = re.search(r'^---\s*\n.*?title:\s*(.*?)\n', content[:500], re.DOTALL)
    title = m.group(1).strip() if m else 'untitled'
    slug = re.sub(r'[^\w\u4e00-\u9fa5]+', '-', title.lower()).strip('-')[:60]
    filename = slug + '.md'
    path = f'{DIR}/{filename}'
    # 检查是否已存在
    sha = None
    try:
        d = gh('GET', f'/repos/{REPO}/contents/{ep(path)}')
        if d: sha = d.get('sha')
    except: pass
    body = {'message': f'Publish: {title}', 'content': b64e(content), 'branch': BRANCH}
    if sha: body['sha'] = sha
    gh('PUT', f'/repos/{REPO}/contents/{ep(path)}', body)
    print(f'✅ 已发布: {filename}')

def delete(name):
    filename = name if name.endswith('.md') else name + '.md'
    path = f'{DIR}/{filename}'
    try:
        d = gh('GET', f'/repos/{REPO}/contents/{ep(path)}')
        if not d: raise SystemExit(f'❌ 文件不存在: {filename}')
        gh('DELETE', f'/repos/{REPO}/contents/{ep(path)}',
           {'message': f'Delete: {filename}', 'sha': d['sha'], 'branch': BRANCH})
        print(f'✅ 已删除: {filename}')
    except SystemExit: raise
    except Exception as e:
        raise SystemExit(f'❌ 删除失败: {e}')

def edit(name, filepath):
    if not os.path.isfile(filepath):
        raise SystemExit(f'❌ 文件不存在: {filepath}')
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    filename = name if name.endswith('.md') else name + '.md'
    path = f'{DIR}/{filename}'
    has_fm = re.match(r'^---\s*\n', content)
    if not has_fm:
        # 保留原标题
        try:
            d = gh('GET', f'/repos/{REPO}/contents/{ep(path)}')
            old = b64d(d['content'])
            m = re.search(r'^---\s*\n.*?title:\s*(.*?)\n', old[:500], re.DOTALL)
            title = m.group(1).strip() if m else filename.replace('.md','')
        except:
            title = filename.replace('.md','')
        today = __import__('datetime').date.today().isoformat()
        fm = f'---\ntitle: {title}\ndate: {today}\ndraft: false\n---\n\n'
        content = fm + content
    try:
        d = gh('GET', f'/repos/{REPO}/contents/{ep(path)}')
        if not d: raise SystemExit(f'❌ 文件不存在: {filename}')
        gh('PUT', f'/repos/{REPO}/contents/{ep(path)}',
           {'message': f'Edit: {filename}', 'content': b64e(content),
            'sha': d['sha'], 'branch': BRANCH})
        print(f'✅ 已更新: {filename}')
    except SystemExit: raise
    except Exception as e:
        raise SystemExit(f'❌ 编辑失败: {e}')

def main():
    if not TOKEN:
        print('⚠️  请设置环境变量 GH_TOKEN 或 GITHUB_TOKEN')
        print('    export GH_TOKEN=ghp_xxxx')
        sys.exit(1)
    if len(sys.argv) < 2:
        print('用法:')
        print('  python blog.py list                    # 列出文章')
        print('  python blog.py publish <file.md>       # 发布本地文件')
        print('  python blog.py delete <slug>           # 删除文章')
        print('  python blog.py edit <slug> <file.md>   # 编辑文章')
        print('')
        print('环境变量:')
        print('  GH_TOKEN       GitHub Token (必填)')
        print('  GH_REPO        仓库名，默认 Ilyfalt/Ilyfalt.github.io')
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == 'list':
        posts = list_posts()
        if not posts:
            print('📭 暂无文章')
        else:
            print(f'📂 content/posts/（共 {len(posts)} 篇）')
            for name, icon in posts:
                print(f'  {icon} {name}')
    elif cmd == 'publish':
        if len(sys.argv) < 3: raise SystemExit('用法: blog.py publish <file.md>')
        publish(sys.argv[2])
    elif cmd == 'delete':
        if len(sys.argv) < 3: raise SystemExit('用法: blog.py delete <slug>')
        delete(sys.argv[2])
    elif cmd == 'edit':
        if len(sys.argv) < 4: raise SystemExit('用法: blog.py edit <slug> <file.md>')
        edit(sys.argv[2], sys.argv[3])
    else:
        print(f'❌ 未知命令: {cmd}')

if __name__ == '__main__':
    main()