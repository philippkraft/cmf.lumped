"""
CMF-Model for Nidder / Glauberg
===============================

by Philipp Kraft

last modification: 2021-01-21 09:27

This text is from the doc-string of the Model's module
"""

import os
import cmf
from cmflumped.basemodel import BaseParameters, u, BaseModel, DocClass
from cmflumped.dataprovider import load_csv
from cmflumped.doctools.result import BaseResult


# The concept class is only used for documentation purposes.
class Concept:
    """
    Concept for {name}
    ==================

    Using the concept of a simple overflowing bucket,
    the model does not generate any baseflow.

    The implementation idea is shown in {fig_ref:concept}, and is based on the model id 01
    from {bib_ref:MARRMoT}, the Collie River Basin 1


    {figure:concept;A simple figure showing the connections in the model}

    """



class Parameters(BaseParameters):
    """
    Implementation
    ---------------

    Model parameters
    ................
    """
    infiltration_capacity = u(
        0, 50, 10,
        doc='Infiltration capacity over a day in mm/day')
    infiltration_w0 = u(
        0.5, 0.99, default=0.75,
        doc=':math:`W_0` saturation index'
    )
    soil_capacity = u(
        10, 500, default=100,
        doc='Capacity of rooted zone in :math:`mm`'
    )
    Sfc = u(0.0, 1.0, default=0.5, doc='Fraction of capacity at field capacity in mm/mm. field capicty = Sfc * Smax')
    ETV1 = u(
        0.1, 0.9, default=0.5,
        doc='Fraction of soil capacity where ET starts to be limited'
    )
    retention_time = u(
        1, 150, default=10,
        doc='Retention time in the catchment water storage'
    )


class Model1(BaseModel):
    """
    The model class
    ...............

    This class implements the specific cmf model using the following methods

    {Class}

    The CMF-Project
    ...............
    """
    verbose = True
    calibration_start = 2000
    validation_start = 2010
    parameters = Parameters()

    def __init__(self):
        path = os.path.dirname(__file__)
        # date,Q,ETpot,P,air_temp_proxy,soil_temperature_5cm
        data = load_csv(os.path.join(path, 'glauburg_temp.csv'),
                        date=0, P=2, E=1, Tmin=3, Q=0)
        
        # Call BaseModel.__init__, which does the following
        #   self.project = cmf.project
        #   self.cell = self.project.NewCell(0, 0, 0, 1000)
        #   self.create_nodes()
        
        super().__init__(data)

    def create_nodes(self):
        """
        Create the nodes (storages, distribution nodes and boundaries) of your model.

        Called from model initialization (self.__init__)
        """
        # Create a subsurface storage
        self.soil = self.cell.add_layer(1)
        self.soil.Name = 'Soil'
        # Make an outlet
        self.outlet = self.project.NewOutlet('outlet', 2, 0, -1)

    def create_result_structure(self):
        """
        Creates the container to store the results in.

        Called, when the run time loop starts
        """
        outflow = cmf.timeseries(self.data.begin, cmf.day)
        outflow.add(self.outlet(self.data.begin))
        return outflow

    def fill_result_structure(self, result, t):
        """
        Fills the result structure with data.

        Called in each timestep.
        """
        q = self.output(t)
        result.add(q)
        if self.verbose:
            print(f'{t!s:>12s} Q={q:10.5g}mm/day')

    def set_soil_capacity(self, p: Parameters)->float:
        """
        Sets the upper soil capacity
        """
        # Parameterize soil water capacity
        self.soil.soil.porosity = p.soil_capacity / (1000 * self.soil.thickness)
        # Set initial value
        self.soil.volume = 0.5 * p.soil_capacity
        # Just a shortcut for the next connections
        return self.soil.get_capacity()

    def create_connections(self, p: Parameters):
        """
        Creates the connections and parameterizes the storages of the model
        """
        # Infiltration
        cmf.SimpleInfiltration(self.soil, self.cell.surfacewater, W0=p.infiltration_w0)
        # Route infiltration / saturation excess to outlet
        cmf.waterbalance_connection(self.cell.surfacewater, self.outlet)

        capacity = self.set_soil_capacity(p)

        cmf.timeseriesETpot(self.soil, self.cell.transpiration, self.data.ETpot)

        # Parameterize infiltration capacity
        self.soil.soil.Ksat = p.infiltration_capacity / 1000

        # Parameterize water stress function
        self.cell.set_uptakestress(cmf.VolumeStress(
            p.ETV1 * capacity, 0)
        )

    def initial_values(self, p: Parameters = None):
        """
        Is called before a simulation starts and should reset
        every storage of the model and needs to be defined for each model
        :param p: The parameters object. May or may not be used in the function
        :return: None
        """

        self.soil.volume = self.soil.get_capacity() * 0.5

    def output(self, t):
        """
        Defines what the ouput of the model is

        :param t: Time step of the model
        :return: A value representing the model output
        """
        return self.outlet.waterbalance(t)

class Result(BaseResult):
    """
    Results for {module}
    ======================================

    Nash-Sutcliffe-Efficiancy and PBIAS for the run with the
    lowest NSE during calibration period

    :Calibration ({setup.calibration_start}-{setup.validation_start}):  NSE={NSE_c:3g}, PBIAS={PBIAS_c:3g}%
    :Validation ({setup.validation_start}-{setup.data.end.year}):  NSE={NSE_v:3g}, PBIAS={PBIAS_v:3g}%

    With a rejection criteria of NSE < {threshold:0.4g}
    {n} runs have been accepted.

    The modelled timeseries of runoff is shown in {fig_ref:timeseries}.

    {figure:timeseries;
        Modelled vs. observed runoff in mm/day.

        Red line - best model run, yellow area - 5th - 95th percentile area of {n} runs
        with an NSE > {threshold:0.4g}, black dotted line is the observed runoff
    }

    The distribution of parameters is shown in {fig_ref:dotty}

    {figure:dotty;The parameter distributions of the accepted parameter sets}
    """

    def __init__(self, model, outputdir='.'):
        """
        :param doc_dir: The directory to save the figures
        """
        super().__init__(model, outputdir=outputdir)


class Discussion(DocClass):
    """
    Discussion
    ----------

    .. todo::
       {module}: Diskussion beschreiben, Namen für Vergleich austauschen

    Die Ergebnisse aus {fig_ref:timeseries} sind immer noch besser als von Philipp {fig_ref:timeseries;philipp}.
    Das liegt daran, ...

    """

class Bibliography(DocClass):
    """
    References
    ----------

    {bib_item:MARRMoT;https://doi.org/10.5194/gmd-12-2463-2019;Knoben et al: Modular Assessment of Rainfall–Runoff Models Toolbox (MARRMoT) v1.2}

    """

if __name__ == '__main__':
    from cmflumped import commands as cmd
    # m = Model1()
    # Starts the graphic user interface for manual calibration.
    # In Spyder: Make sure to run this in an external terminal (Ctrl + F6)
    cmd.doc(__file__, in_browser=True)
    

