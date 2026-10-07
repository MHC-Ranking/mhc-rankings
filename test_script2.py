from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin
import re

md = MarkdownIt("commonmark").use(dollarmath_plugin, double_inline=True)
res = md.render("hello $$r_i$$ world \n\n $$ block $$")
print(res)
