# -*- coding: utf-8 -*-
"""
Ein 2-Speicher lumped Modell für das Einzugsgebiet der Fulda
===============================================================

:author: Philipp Kraft, Mat-Nr: xxxxx-xxxxx



"""
import cmf
import spotpy
from spotpy.parameter import Uniform, Constant
import numpy as np
import datetime
import importlib.util
import os
import sys
from .dataprovider import DataProvider
from .doctools import DocClass

def load_module_from_path(path_to_module:str):
    """
    Loads a module from a path
    :param path_to_module:
    :return:

    See: https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
    """
    name = os.path.basename(path_to_module).replace('.py', '')
    spec = importlib.util.spec_from_file_location(name, path_to_module)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)

    return module


def get_model_class(path_to_module:str, classname=None):
    """
    This function get the class of a lumped cmf model from
    a Python file
    :param path_to_module: The file path to the module
    :param classname: A classname, if None the first childclass of BaseModel is returned
    :return: The model class
    """

    module = load_module_from_path(path_to_module)
    if classname:
        return getattr(module, classname)
    else:
        # Loop through all members of the module and detect a class that is derived
        # from the cmflumped.BaseModel
        for name, obj in vars(module).items():
            if (
                    name[0] != '_'
                    and isinstance(obj, type)
                    and obj is not module.BaseModel
                    and issubclass(obj, module.BaseModel)
            ):
                return obj
        # Raise Error if no fitting class is found
        raise ValueError(f'Module "{path_to_module}" has no class that derives from cmflumped.BaseModel')


def u(vmin, vmax, default=None, doc=None):
    """
    Creates a uniform distributed parameter
    :param vmin: Minimum value
    :param vmax: Maximum value
    :param default: Default value
    :param doc: Documentation of the parameter (use reStructuredText)
    :return: The parameter object
    """
    if default is None:
        default = 0.5 * (vmin + vmax)
    return Uniform(vmin, vmax, optguess=default, doc=doc, minbound=vmin, maxbound=vmax)


def constant(vmin, vmax, default=None, doc=None):
    if default is None:
        default = 0.5 * (vmin + vmax)
    return Constant(default, optguess=default, minbound=vmin, maxbound=vmax, doc=doc)


class BaseParameters:

    def __get__(self, instance, owner):
        # A magic method for simple use of this object
        return spotpy.parameter.get_parameters_from_setup(self)

    @classmethod
    def to_string(cls):
        params = cls()
        return cls.__doc__ + '\n'.join(
            f':{p.name}: [{p.minbound:0.4g}..{p.maxbound:0.4g}] {p.description}'
            for p in spotpy.parameter.get_parameters_from_setup(params)
        )

class BaseModel(DocClass):
    """
    The template for
    """

    verbose = True
    calibration_start = 2000
    validation_start = 2010

    def __init__(self, dataprovider: DataProvider, name: str = None):
        """
        Creates the basic structure of the model
        """
        self.data = dataprovider
        self.name = name or self.__module__
        self.project = cmf.project()
        self.cell: cmf.Cell = self.project.NewCell(0, 0, 0, 1000)

        self.create_nodes()
        self.data.add_stations(self.project)
        self.create_connections(spotpy.parameter.create_set(self, 'optguess'))

# OVERRIDE ->
    def create_nodes(self):
        """
        Create the nodes (storages, distribution nodes and boundaries) of your model.

        eg.

        .. code-block::

            self.soil, self.gw = self.add_layers(1.0, 1.0)
            self.outlet = self.project.NewOutlet('outlet' , 0, 0, 0)

        or something else
        """
        ...

    def create_connections(self, p):
        ...

    def initial_values(self, p):
        """
        Is called before a simulation starts and should reset
        every storage of the model and needs to be defined for each model
        :param p: The parameters object. May or may not be used in the function
        :return: None
        """
        ...

    def create_result_structure(self):
        outflow = cmf.timeseries(self.data.begin, cmf.day)
        outflow.add(self.outlet(self.data.begin))
        return outflow

    def fill_result_structure(self, result, t):
        q = self.output(t)
        result.add(q)
        if self.verbose:
            print(f'{t!s:>12s} Q={q:10.5g}mm/day')
# <- OVERRIDE
    def add_layers(self, *thickness):
        return tuple(
            self.cell.add_layer(d)
            for d in np.cumsum(thickness)
        )

    def iterate(self, p = None):
        """
        Calls `create_connections` and `inital_values` to shape
        the model using the parameter set `p` and returns an
        iterator that advances the model over the whole data period
        """
        self.create_connections(p)
        self.initial_values(p)

        solver = cmf.CVodeIntegrator(self.project, 1e-9)
        solver.use_OpenMP = False
        return solver.run(self.data.begin, self.data.end, cmf.day)

    def output(self, t):
        """
        Defines what the ouput of the model is
        :param t: Time step of the model
        :return: A value representing the model output
        """
        return self.outlet.waterbalance(t)

    def __str__(self):
        return self.name

    def simulation(self, vector):
        """
        This function is only important for spotpy,
        otherwise it is equivalent with "run"
        :param vector:
        :return:
        """
        result = self.create_result_structure()
        duration = datetime.datetime.now()

        for t in self.iterate(vector):
            self.fill_result_structure(result, t)
        result_array = np.array(result)
        if self.verbose:
            print('objective: NSE_c={:0.4g}, NSE_v={:0.4g}, PBIAS_c={:0.4g}, PBIAS_v={:0.4g}'.format(*self.objectivefunction(result_array, self.evaluation())))
            print('duration:', datetime.datetime.now() - duration)
        return result_array

    def evaluation(self):
        """
        Returns the evaluation data
        """
        runoff = self.data.Q
        return np.array(runoff)

    def objectivefunction(self, simulation, evaluation):
        """
        Calculates the goodness of the simulation

        Calculates
         - :math:`NSE_c`: the Nash-Sutcliffe Efficiancy
            for the calibration period (self.begin:self.end)
         - :math:`PBIAS_c`: the procentual bias between model and observation
            for the calibration period (self.begin:self.end)
         - :math:`NSE_v`: the Nash-Sutcliffe Efficiancy
            for the validation period (self.end:self.data.end)
         - :math:`PBIAS_v`: the procentual bias between model and observation
            for the validation period (self.end:self.data.end)

        and returns these objectives as a list in that order
        """

        def getindex(year):
            """
            Returns the array position for Jan 1st of the respective year
            :param year: a year
            :return: int
            """
            dt = datetime.datetime(year, 1, 1)
            return (dt - self.data.begin).days

        c_start = getindex(self.calibration_start)
        v_start = getindex(self.validation_start)
        nse_c = spotpy.objectivefunctions.nashsutcliffe(evaluation[c_start:v_start], simulation[c_start:v_start])
        pbias_c = spotpy.objectivefunctions.pbias(evaluation[c_start:v_start], simulation[c_start:v_start])
        nse_v = spotpy.objectivefunctions.nashsutcliffe(evaluation[v_start:], simulation[v_start:])
        pbias_v = spotpy.objectivefunctions.pbias(evaluation[v_start:], simulation[v_start:])

        return [nse_c, nse_v, pbias_c, pbias_v]


    @property
    def begin(self):
        return self.data.begin

    @property
    def end(self):
        return self.data.end



