from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin

md = MarkdownIt("commonmark").use(dollarmath_plugin)
res = md.render("hello $r_i$ world \n\n $$ block $$")

with open("test_output.txt", "w") as f:
    f.write(res)
