from .basemodel import get_model_class as _get_model_class
from .basemodel import BaseModel as _BaseModel


def gui(model):
    """
    Opens a gui to run and explore the model
    Usage: cmflumped doc <model.py>
           <model.py>: The Python file containing the model
    """
    from cmflumped.gui import GUI
    m = _get_model_class(model)()
    with GUI(m) as mgui:
        mgui.show()


def result(*setups):
    """
    Loads and analyses the result file from cmf.lumped run model.py 10000
    """
    from .doctools.result import BaseResult
    for model in setups:
        m = _get_model_class(model)()
        r: BaseResult
        Result = _get_model_class(model, 'Result')
        with Result(m, '.') as r:
            r.save(verbose=True)


def doc(*setups, in_browser=False):
    """
    Creates documentation files for the model
    Usage: cmflumped doc <model.py>
           <model.py>: The Python file containing the model
    """
    import matplotlib as mpl
    mpl.use('Agg')
    from cmflumped.doctools import Documentation
    # Schreibe die rst-Dateien
    for setup in setups:
        model = _get_model_class(setup)()
        docu = Documentation(model)
        docu.make_rst()
        # Erzeuge die HTML-Dokumentation
        build_dir = docu.compile_html()

    if in_browser:
        import webbrowser
        webbrowser.open((build_dir / 'html' / 'index.html').as_uri())


def descr(model):
    """
    Prints out a description of your model
    Usage: cmflumped descr <model.py>
           <model.py>: The Python file containing the model
    """
    import cmf
    m = _get_model_class(model)()
    print(cmf.describe(m.project))


def run(model, runs=None, sampler='lhs'):
    """
    Runs the model
    Usage: cmf.lumped run <model.py> [runs] [sampler]
           <model.py>: The Python file containing the model
           [runs]: Number of runs (default=1)
           [sampler]: spotpy sampler to use,
                eg. mc (Monte Carlo), lhs (latin hypercube sampling), dds - see spotpy documentation

    Example:
        Single run:
            cmf.lumped run example/model1.py
        Many runs:
            cmf.lumped run example/model1.py 1000 lhs
    """
    from cmflumped.spotpy_helper import sample
    m: _BaseModel = _get_model_class(model)()
    m.verbose = not runs
    if runs:
        n = int(runs)
        sample(m, n, sampler, save_threshold=0.0)
    else:
        from spotpy.parameter import create_set
        p = create_set(m, 'optguess')
        m.simulation(p)

