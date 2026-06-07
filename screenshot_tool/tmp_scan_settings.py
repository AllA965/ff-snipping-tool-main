import ast
import json
from pathlib import Path

src = Path('ui/settings_dialog.py').read_text(encoding='utf-8')
tree = ast.parse(src)
strings = []

class V(ast.NodeVisitor):
    def visit_Call(self, node):
        # tr("...")
        if isinstance(node.func, ast.Name) and node.func.id == 'tr' and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                s = arg.value
                if any('\u4e00' <= ch <= '\u9fff' for ch in s):
                    strings.append(s)
        self.generic_visit(node)

V().visit(tree)
strings = sorted(set(strings))
print('TR_STRINGS')
for s in strings:
    print(repr(s))
print('COUNT', len(strings))

en = json.loads(Path('locales/en.json').read_text(encoding='utf-8'))
print('MISSING_IN_EN')
for s in strings:
    if s not in en:
        print(repr(s))
