from textwrap import dedent


class DocFunction:
    def __init__(self, template, **kwargs):
        self.kwargs: dict = kwargs
        self.template = dedent(template)

    def __format__(self, format_spec):
        kwargs = self.kwargs.copy()
        args = []
        pair: str
        for item in format_spec.split(';'):
            if '=' in item:
                k, v = item.split('=', 1)
                kwargs[k.strip()] = v.strip()
            elif item:
                args.append(item.strip())

        for k, a in zip(self.kwargs, args):
            kwargs[k] = a

        return self.template.format(**kwargs)


class DocClass:
    figure = DocFunction(
        """
        .. _fig-{module}-{name}:

        .. figure:: {module}.{name}.{ext}
            :width: 800px
            :align: center
            :figclass: align-center

            {description}
        """, name='', description='', module='', ext='png')

    fig_ref = DocFunction(':numref:`fig-{module}-{name}`', name='')

    bib_ref = DocFunction('[{module}-{shortcut}]_', shortcut='')

    bib_item = DocFunction('.. [{module}-{shortcut}] {title} {doi}', shortcut='', doi='', title='')

    Class = DocFunction("""
    .. autoclass:: {module}.{classname}
        :members:
    """)

    @classmethod
    def describe(cls, setup=None, **kwargs) -> str:
        template = dedent(cls.__doc__)
        module = setup and setup.name
        classname = setup and setup.__class__.__name__
        docfunctions = {
            k: getattr(cls, k) for k in dir(cls)
            if isinstance(getattr(cls, k), DocFunction)
        }

        for dcf in docfunctions.values():
            dcf.kwargs['module'] = module
            dcf.kwargs['classname'] = classname
            dcf.kwargs['setup'] = setup

        return template.format(setup=setup, module=module, classname=classname, **docfunctions, **kwargs)
