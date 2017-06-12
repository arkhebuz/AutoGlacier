import jinja2
from autoglacier.ag_command import _construct_argparse_parser


readme_template = """
{% for title, help_msg in my_help %}
{{ title }}

```{{ help_msg }}```

{% endfor %}
"""

latex_jinja_env = jinja2.Environment(autoescape = False)
template = latex_jinja_env.from_string(readme_template)


sections = ["## AutoGlacier", 
            '### `autoglacier init`', 
            '### `autoglacier register`', 
            '### `autoglacier job`', 
            '### `autoglacier config`']
parsers = _construct_argparse_parser(return_all_parsers=1)
helps = [p.format_help() for p in parsers]
with open("README.md", 'w') as f:
    f.write(template.render(my_help=zip(sections, helps)))
