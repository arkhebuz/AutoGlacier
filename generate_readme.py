import jinja2
from glacierbackup.command import _construct_argparse_parser


preamble = """
# GlacierBackup
A tool to track small files and back them up into Glacier enabling disaster-recovery document
 backups at virtually no cost - installable via pip:
```
$ pip install glacierbackup
```

What follows is an overview of a CLI interface.
"""


readme_template = """
{% for title, help_msg in my_help %}
{{ title }}

```{{ help_msg }}```

{% endfor %}
"""

latex_jinja_env = jinja2.Environment(autoescape = False)
template = latex_jinja_env.from_string(readme_template)


sections = [preamble, 
            '### `glacierbackup init`', 
            '### `glacierbackup register`', 
            '### `glacierbackup job`', 
            '### `glacierbackup config`']
parsers = _construct_argparse_parser(return_all_parsers=1)
helps = [p.format_help() for p in parsers]
with open("README.md", 'w') as f:
    f.write(template.render(my_help=zip(sections, helps)))
