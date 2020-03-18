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
    GUI(m).show()


def doc(setup):
    """
    Creates documentation files for the model
    Usage: cmflumped doc <model.py>
           <model.py>: The Python file containing the model
    """
    from cmflumped.doctools import create_rst, do_sphinx
    # Schreibe die rst-Dateien
    model = _get_model_class(setup)()
    create_rst(model)
    # Erzeuge die HTML-Dokumentation
    do_sphinx(model)


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
    if runs:
        n = int(runs)
        sample(m, n, sampler)
    else:
        from spotpy.parameter import create_set
        p = create_set(m, 'optguess')
        m.simulation(p)

