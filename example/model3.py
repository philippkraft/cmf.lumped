"""
[Your Name]
===========

Use a few sentences to introduce your model. The concept description follows later

"""


import os
import cmf
from cmflumped.basemodel import BaseParameters, u, BaseModel, constant, DocClass
from cmflumped.dataprovider import load_csv
from cmflumped.doctools.result import BaseResult


class Concept(DocClass):
    """
    Concept for {module}
    ---------------------------------

    A lumped model with snow, distinct
    soil and groundwater storages. Baseflow occurs from the groundwater,
    surface runoff is triggered by infiltration excess and / or saturation
    excess.

    The implementation idea is shown in {fig_ref:concept;ext=jpg}, and is based on the XX model
    from {bib_ref:MARRMoT}


    {figure:concept;A simple figure showing the connections in the model}

    """


class Parameters(BaseParameters):
    """
    Implementierung
    ---------------

    Model parameters
    ................
    """
    snow_melt_rate = u(
        3, 10, default=7,
        doc='Rate of snow melt in :math:`\\frac{mm}{day °C}`'
    )
    infiltration_capacity = constant(0, 30, 30, 'Dokumentation...')

    infiltration_w0 = constant(
        0.5, 0.99, default=0.95,
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

    Q0 = u(
        0.01, 50, default=10,
        doc='Percolation rate in :math:`mm/day` when the soil stores contains' +
            ':math:`V_0 \cdot C [mm]` water'
    )
    V0 = u(
        0.01, 1.0, default=0.5,
        doc='*Normal* soil water content in terms of soil water capacity'
    )
    Vres = u(
        0.0, 1.0, default=0.1,
        doc='Residual water content of the soil water'
    )
    beta = u(
        0.5, 5, default=3,
        doc='Curve shape parameter of the power law function'
    )

    perc_rate = u(0, 10, 1, 'Percolation rate in mm/day')
    gw_residence_time = u(10, 1000, 200, 'Residence time of groundwater in days')


class Model3(BaseModel):
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

    def __init__(self, name: str = None):
        path = os.path.dirname(__file__)
        data = load_csv(os.path.join(path, 'glauburg_temp.csv'),
                        date=0, P=2, E=1, Tmin=3, Q=0)
        super().__init__(data, name)

    def create_nodes(self):
        """
        Create the nodes (storages, distribution nodes and boundaries) of your model.
        """
        # Create two subsurface storages
        self.soil = self.cell.add_layer(1)
        self.soil.Name = 'Soil'

        self.gw = self.cell.add_layer(2)
        self.gw.Name = 'GW'

        # Create a storage for snow
        self.cell.add_storage(f'Snow', 'S')
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
        # Percolation
        cmf.ConstantFlux(self.soil, self.gw, p.perc_rate, 0, cmf.week)

        # GW to outlet
        cmf.LinearStorageConnection(self.gw, self.outlet, p.gw_residence_time)


        # Interflow
        cmf.PowerLawConnection(
            self.soil, self.outlet,
            Q0=p.Q0,
            V0=p.V0 * C,
            beta=p.beta,
            residual=p.Vres * C,
        )

    def initial_values(self, p: Parameters = None):
        self.soil.volume = self.soil.get_capacity() * p.V0
        self.gw.volume = 0.1 * p.gw_residence_time
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
    import logging
    logger = logging.getLogger(__file__)
    logging.basicConfig(level=logging.DEBUG)
    print(__file__)
    m = Model3('model3')
    from cmflumped.doctools import Documentation
    docu = Documentation(m)
    docu.make_rst()
    docu.compile_html()



