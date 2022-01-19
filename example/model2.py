"""
CMF-Model for Nidder / Glauberg
===============================

by Philipp Kraft

last modification: 2021-01-21 09:27

This text is from the doc-string of the Model's module
"""


import os
import cmf
from cmflumped.basemodel import BaseParameters, u, BaseModel
from cmflumped.dataprovider import load_csv
from cmflumped.doctools.result import BaseResult


class Concept:
    """
    Concept for Model2
    ==================

    A lumped model with an interception storage, snow, distinct
    soil and groundwater storages. Baseflow occurs from the groundwater,
    surface runoff is triggered by infiltration excess and / or saturation
    excess.

    The implementation idea is shown in {fig_ref:concept}, and is based on the model id 13
    from {bib_ref:MARRMoT},


    {figure:concept;A simple figure showing the connections in the model}

    """
    ...



class Parameters(BaseParameters):
    """
    A helper class to define the parameters of the model

    Create class owned fields as parameters
    """
    snow_melt_rate = u(
        3, 10, default=7,
        doc='Rate of snow melt in :math:`\\frac{mm}{day °C}`'
    )
    infiltration_capacity = u(0, 20, 10, 'Dokumentation...')
    infiltration_w0 = u(
        0.5, 0.99, default=0.75,
        doc=':math:`W_0` saturation index'
    )
    soil_capacity = u(
        10, 500, default=100,
        doc='Capacity of rooted zone in :math:`mm`'
    )
    ETV1 = u(
        0.1, 0.9, default=0.5,
        doc='Fraction of soil capacity where ET starts to be limited'
    )
    percolation_Q0 = u(
        0.01, 50, default=10,
        doc='Percolation rate in :math:`mm/day` when the soil stores contains' +
            ':math:`V_0 \cdot C [mm]` water'
    )
    percolation_V0 = u(
        0.01, 1.0, default=0.5,
        doc='*Normal* soil water content in terms of soil water capacity'
    )
    percolation_Vres = u(
        0.0, 1.0, default=0.1,
        doc='Residual water content of the soil water'
    )
    percolation_beta = u(
        0.5, 5, default=3,
        doc='Curve shape parameter of the power law function'
    )
    groundwater_residence_time = u(
        1, 100, default=100,
        doc='Residence time of the groundwater in days'
    )
    LAI = u(
        0.5, 6, default=3,
        doc='Effective leaf area index'
    )
    canopy_closure = u(
        0.0, 1.0, default=0.5,
        doc='Fraction of rainfall that stays in the canopy'
    )


class Model2(BaseModel):
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
        data = load_csv(os.path.join(path, 'glauburg_temp.csv'),
                        date=0, P=2, E=1, Tmin=3, Q=0)
        super().__init__( data)

    def create_nodes(self):
        """
        Create the nodes (storages, distribution nodes and boundaries) of your model.
        """
        # Create two subsurface storages
        self.soil = self.cell.add_layer(1)
        self.gw = self.cell.add_layer(2)

        self.soil.Name = 'Soil'
        self.gw.Name = 'GW'

        # Create a storage for snow
        self.cell.add_storage(f'Snow', 'S')
        # Create a canopy storage
        self.cell.add_storage(f'Canopy', 'C')
        # Make an outlet
        self.outlet = self.project.NewOutlet('outlet', 2, 0, -1)

    def create_result_structure(self):
        outflow = cmf.timeseries(self.data.begin, cmf.day)
        outflow.add(self.outlet(self.data.begin))
        return outflow

    def fill_result_structure(self, result, t):
        q = self.output(t)
        result.add(q)
        if self.verbose:
            print(f'{t!s:>12s} Q={q:10.5g}mm/day')

    def create_snow_connections(self, p: Parameters):
        """
        Divides snowfall and rainfall based on temperature
        and calculates the snow melt rate using a simple
        temperature index melting model
        :param p: The model parameters, here only p.snow_melt_rate is used
        """

        cmf.Snowfall(self.cell.snow, self.cell)
        cmf.Rainfall(self.cell.surfacewater, self.cell)
        cmf.SimpleTindexSnowMelt(self.cell.snow, self.cell.surfacewater,
                                 self.cell, rate=p.snow_melt_rate)

    def create_surface_runoff(self, p: Parameters):
        """
        Models infiltration with a mixed saturation / infiltration excess model
        and routes all runoff directly without timelag to the outlet
        """
        # Infiltration
        cmf.ConceptualInfiltration(self.soil, self.cell.surfacewater, W0=p.infiltration_w0)
        # Route infiltration / saturation excess to outlet
        cmf.waterbalance_connection(self.cell.surfacewater, self.outlet)

    def set_soil_capacity(self, p: Parameters):
        """
        Sets the upper soil capacity
        """
        # Parameterize soil water capacity
        self.soil.soil.porosity = p.soil_capacity / (1000 * self.soil.thickness)
        # Set initial value
        self.soil.volume = 0.5 * p.soil_capacity
        # Just a shortcut for the next connections
        return self.soil.get_capacity()

    def create_canopy_connections(self, p: Parameters):
        """
        Connects the canopy with the rainfall and the surface
        depending on vegetation parameters
        """
        cmf.CanopyStorageEvaporation(self.cell.canopy, self.cell.evaporation, self.cell)
        cmf.RutterInterception(self.cell.canopy, self.cell.surfacewater, self.cell)
        cmf.Rainfall(self.cell.surfacewater, self.cell, True, False)
        cmf.Rainfall(self.cell.canopy, self.cell, False, True)
        self.cell.vegetation.LAI = p.LAI
        self.cell.vegetation.CanopyClosure = p.canopy_closure

    def create_connections(self, p: Parameters):
        """
        Creates the connections and parameterizes the storages of the model

        """

        # Route snow melt to surface
        if self.cell.snow:
            self.create_snow_connections(p)
        self.create_surface_runoff(p)
        C = self.set_soil_capacity(p)

        cmf.timeseriesETpot(self.soil, self.cell.transpiration, self.data.ETpot)
        # Parameterize water stress function

        self.soil.soil.Ksat = p.infiltration_capacity / 1000

        self.cell.set_uptakestress(cmf.VolumeStress(
            p.ETV1 * C, 0)
        )

        if self.cell.canopy:
            self.create_canopy_connections(p)

        # Route water from soil to gw
        cmf.PowerLawConnection(
            self.soil, self.gw,
            Q0=p.percolation_Q0,
            V0=p.percolation_V0 * C,
            beta=p.percolation_beta,
            residual=p.percolation_Vres * C,
        )
        # Route water from gw to outlet
        cmf.LinearStorageConnection(
            self.gw, self.outlet,
            residencetime=p.groundwater_residence_time,
            residual=0
        )

    def initial_values(self, p: Parameters = None):
        self.soil.volume = self.soil.get_capacity() * p.percolation_V0
        self.gw.volume = 1.0
        self.cell.snow.volume = 0.0

    def output(self, t):
        """
        Defines what the ouput of the model is
        :param t: Time step of the model
        :return: A value representing the model output
        """
        return self.outlet.waterbalance(t)


class Result(BaseResult):
    """
    Results for {self.name}
    ======================================

    Nash-Sutcliffe-Efficiancy and PBIAS for the run with the
    lowest NSE during calibration period

    :Calibration ({CStart}-{CEnd}):  NSE={like1:3g}, PBIAS={like3:3g}%
    :Validation ({VStart}-{VEnd}):  NSE={like2:3g}, PBIAS={like4:3g}%

    With a rejection criteria of NSE < {self.threshold:0.4g}
    {self.n} runs have been accepted.

    The modelled timeseries of runoff is shown in :numref:`fig-{name}-timeseries`.

    .. fig-{name}-timeseries:

    .. figure:: {name}.timeseries.png
        :width: 800px

        Modelled vs. observed runoff in mm/day.

        Red line - best model run, yellow area - 5th - 95th percentile area of {self.n} runs
        with an NSE > {self.threshold:0.4g}, black dotted line is the observed runoff

    The distribution of parameters is shown in :numref:`fig-{name}-dotty`

    .. _fig-{name}-dotty:

    .. figure:: {name}.dotty.png
        :width: 800px

        The parameter distributions of the accepted parameter sets

    """

    def __init__(self, model, outputdir):
        """
        :param doc_dir: The directory to save the figures
        """
        super().__init__(model, outputdir=outputdir)
        self.dotty_plot()
        self.timeseries_plot()

    def __str__(self):
        best_run = self.best_run_id()
        like1, like2, like3, like4 = self.like(best_run)
        return self.format_doc_string(
            like1=like1, like2=like2, like3=like3, like4=like4,
            CStart=self.model.calibration_start,
            CEnd=self.model.validation_start - 1,
            VStart=self.model.validation_start,
            VEnd=self.model.data.end.year,
            self=self
        )

class Discussion:
    """
    Diskussion
    ----------

    .. todo::
       {self.name.capitalize()}: Diskussion beschreiben, Namen für Vergleich austauschen

    Die Ergebniss aus :numref:`fig_{self.name}_timeseries` sind immer noch besser als von Philipp (:numref:`fig_philipp_timeseries`).
    Das liegt daran, ...

    """


if __name__ == '__main__':
    from cmflumped.commands import gui, doc
    import logging
    logger = logging.getLogger(__file__)
    logging.basicConfig(level=logging.DEBUG)
    print(__file__)
    gui(__file__)
    # doc(__file__)