import json
from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin

md = MarkdownIt("commonmark").use(dollarmath_plugin)
with open("rules.json", "w") as f:
    f.write(json.dumps(list(md.renderer.rules.keys())))
