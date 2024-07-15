import os
from typing import (
    TYPE_CHECKING,
)

import numpy as np
import plotly.express as px
import plotly.graph_objs as go
from ase.data import chemical_symbols
from nomad.config import config
from nomad.datamodel.data import ArchiveSection, EntryData, Schema, UseCaseElnCategory
from nomad.datamodel.metainfo.annotations import ELNAnnotation
from nomad.datamodel.metainfo.basesections import (
    CompositeSystem,
    CompositeSystemReference,
    Measurement,
)
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.datamodel.results import (
    Catalyst,
    CatalyticProperties,
    Material,
    Properties,
    Results,
)
from nomad.datamodel.results import Product as Product_result
from nomad.datamodel.results import Reactant as Reactant_result
from nomad.metainfo import (
    Quantity,
    SchemaPackage,
    Section,
    SubSection,
)
from nomad.units import ureg

from .catalyst_measurement import (
    CatalyticReactionData,
    CatalyticReactionData_core,
    Rates,
    ReactionConditions,
    ReactionConditionsSimple,
    ReactorSetup,
    add_activity,
)
from .catalyst_measurement import Product as Product_data
from .catalyst_measurement import Reactant as Reactant_data
from .catalyst_measurement import Reagent as Reagent_data

if TYPE_CHECKING:
    pass


configuration = config.get_plugin_entry_point(
    'nomad_catalysis_test.schema_packages:catalysis'
)

m_package = SchemaPackage()

def add_catalyst(archive):
    '''Adds metainfo structure for catalysis data.'''
    if not archive.results:
        archive.results = Results()
    if not archive.results.properties:
        archive.results.properties = Properties()
    if not archive.results.properties.catalytic:
        archive.results.properties.catalytic = CatalyticProperties()
    if not archive.results.properties.catalytic.catalyst:
        archive.results.properties.catalytic.catalyst = Catalyst()

#helper function to retrieve nested attributes
def get_nested_attr(obj, attr_path):
    for attr in attr_path.split('.'):
        obj = getattr(obj, attr, None)
        if obj is None:
            return None
    return obj

def populate_catalyst_sample_info(archive, self, logger, reference=False):
    '''
    Copies the catalyst sample information from a reference
    into the results archive of the measurement.
    '''
    if reference:
        sample_obj = self.samples[0].reference
    else:
        sample_obj = self

    add_catalyst(archive)
    quantities_results_mapping={
        'name': 'catalyst_name',
        'catalyst_type': 'catalyst_type',
        'preparation_details.preparation_method': 'preparation_method',
        'surface.surface_area': 'surface_area'
    }

    #Loop through the mapping and assign the values
    for ref_attr, catalyst_attr in quantities_results_mapping.items():
        value = get_nested_attr(sample_obj, ref_attr)
        if value is not None:
            try:
                setattr(archive.results.properties.catalytic.catalyst,
                    catalyst_attr, value)
            except ValueError:
                setattr(archive.results.properties.catalytic.catalyst,
                        catalyst_attr, [value])
            except:
                logger.warn('Something else went wrong when trying setattr')
    if reference:
        if self.samples[0].reference.name is not None:
            if not archive.results.material:
                archive.results.material = Material()
            archive.results.material.material_name = self.samples[0].reference.name

        if self.samples[0].reference.elemental_composition is not None:
            if not archive.results.material:
                archive.results.material = Material()
        try:
            archive.results.material.elemental_composition = (
                self.samples[0].reference.elemental_composition)

        except Exception as e:
            logger.warn('Could not analyse elemental compostion.', exc_info=e)

        for i in self.samples[0].reference.elemental_composition:
            if i.element not in chemical_symbols:
                logger.warn(
                    f"'{i.element}' is not a valid element symbol and this "
                    'elemental_composition section will be ignored.'
                )
            elif i.element not in archive.results.material.elements:
                archive.results.material.elements += [i.element]

def add_referencing_methods_to_sample_result(self, archive, logger, number):
    if self.lab_id is not None:
        from nomad.search import MetadataPagination, search
        catalyst_sample = self.m_root().metadata.entry_id
        query = {'entry_references.target_entry_id': catalyst_sample}
        search_result = search(
            owner='all',
            query=query,
            pagination=MetadataPagination(page_size=number),
            user_id=archive.metadata.main_author.user_id,
        )

        if search_result.pagination.total > 0:
            methods = []
            for entry in search_result.data:
                if entry['entry_type'] == 'ELNXRayDiffraction':
                    method = 'XRD'
                    methods.append(method)
                elif entry['entry_type'] == 'CatalystCollection':
                    pass
                elif entry['entry_type'] == 'CatalystSampleCollection':
                    pass
                # else:
                #     method = entry['entry_type']
                #     methods.append(method)
            if search_result.pagination.total > number:
                logger.warn(
                    f'Found {search_result.pagination.total} entries with entry_id:'
                    f' "{catalyst_sample}". Will only check the the first '
                    f'"{number}" entries found for XRD method.'
                )
            if methods:
                if (archive.results.properties.catalytic.catalyst.
                    characterization_methods) is None:
                    (archive.results.properties.catalytic.catalyst.
                        characterization_methods) = []
                (archive.results.properties.catalytic.catalyst.
                    characterization_methods.append(methods[0]))
        else:
            logger.warn(f'Found no entries with reference: "{catalyst_sample}".')


class Preparation(ArchiveSection):
    preparation_method = Quantity(
        type=str,
        shape=[],
        description="""
          Classification of the dominant preparation step
          in the catalyst synthesis procedure.
          """,
        a_eln=dict(
            component='EnumEditQuantity', props=dict(
                suggestions=['precipitation', 'hydrothermal', 'flame spray pyrolysis',
                             'impregnation', 'calcination', 'unknown']),
            links=['https://w3id.org/nfdi4cat/voc4cat_0007016'])
    )

    preparator = Quantity(
        type=str,
        shape=[],
        description="""
        The person or persons preparing the sample in the lab.
        """,
        a_eln=dict(component='EnumEditQuantity')
    )

    preparing_institution = Quantity(
        type=str,
        shape=[],
        description="""
        institution at which the sample was prepared
        """,
        a_eln=dict(component='EnumEditQuantity', props=dict(
            suggestions=['Fritz-Haber-Institut Berlin / Abteilung AC',
                         'Fritz-Haber-Institut Berlin / ISC']))
    )

    def normalize(self, archive, logger):
        super().normalize(archive, logger)


class SurfaceArea(ArchiveSection):
    m_def = Section(
        label_quantity='method_surface_area_determination',
        a_eln=ELNAnnotation(label='Surface Area'))

    surface_area = Quantity(
        type=np.float64,
        unit=("m**2/g"),
        a_eln=dict(
            component='NumberEditQuantity', defaultDisplayUnit='m**2/g',
            links=['https://w3id.org/nfdi4cat/voc4cat_0000013'])
    )

    method_surface_area_determination = Quantity(
        type=str,
        shape=[],
        description="""
          A description of the method used to measure the surface area of the sample.
          """,
        a_eln=dict(
            component='EnumEditQuantity', props=dict(
                suggestions=['BET', 'H2-TPD', 'N2O-RFC',
                             'Fourier Transform Infrared Spectroscopy (FTIR)'
                              ' of adsorbates',
                             'unknown']))
    )

    dispersion = Quantity(
        type=np.float64,
        shape=[],
        description="""
        The dispersion of the catalyst in %.
        """,
        a_eln=dict(component='NumberEditQuantity')
    )

    def normalize(self, archive, logger):
        super().normalize(archive, logger)

        if self.method_surface_area_determination is not None:
            add_catalyst()
            (archive.results.properties.catalytic.catalyst.characterization_methods.
            append(self.method_surface_area_determination))

class CatalystSample(CompositeSystem, Schema):
    m_def = Section(
        label='Heterogeneous Catalysis - Catalyst Sample',
        categories=[UseCaseElnCategory],
    )

    preparation_details = SubSection(section_def=Preparation,
                                     a_eln=ELNAnnotation(label='Preparation Details'))

    surface = SubSection(section_def=SurfaceArea,
                         a_eln=ELNAnnotation(label='Surface Area'))

    storing_institution = Quantity(
        type=str,
        shape=[],
        description="""
        The institution at which the sample is stored.
        """,
        a_eln=dict(component='EnumEditQuantity', props=dict(
            suggestions=['Fritz-Haber-Institut Berlin / Abteilung AC',
                         'Fritz-Haber-Institut Berlin / ISC', 'TU Berlin / BasCat']))
    )

    catalyst_type = Quantity(
        type=str,
        shape=['*'],
        description="""
          A classification of the catalyst type.
          """,
        a_eln=dict(
            component='EnumEditQuantity', props=dict(
                suggestions=['bulk catalyst', 'supported catalyst',
                             'single crystal','metal','oxide',
                             '2D catalyst', 'other', 'unkown']),
        ),
        links=['https://w3id.org/nfdi4cat/voc4cat_0007014'],
    )

    form = Quantity(
        type=str,
        shape=[],
        description="""
          classification of physical form of catalyst
          """,
        a_eln=dict(component='EnumEditQuantity', props=dict(
            suggestions=['sieve fraction', 'powder', 'thin film']),
        ),
        links=['https://w3id.org/nfdi4cat/voc4cat_0000016'],
    )

    def normalize(self, archive, logger):
        from nomad.datamodel.context import ClientContext
        if isinstance(archive.m_context, ClientContext):
            pass
        else:
            super().normalize(archive, logger)

        populate_catalyst_sample_info(archive, self, logger)

        from nomad.datamodel.context import ClientContext
        if isinstance(archive.m_context, ClientContext):
            pass
        else:
            add_referencing_methods_to_sample_result(self, archive, logger, 10)


class ReactorFilling(ArchiveSection):
    m_def = Section(description='A class containing information about the catalyst'
                    ' and filling in the reactor.',
                    label='Catalyst')

    catalyst_name = Quantity(
        type=str, shape=[], a_eln=ELNAnnotation(component='StringEditQuantity'))

    sample_section_reference = Quantity(
        type=CompositeSystemReference, description='A reference to the sample'
         ' used in the measurement.',
        a_eln=ELNAnnotation(component='ReferenceEditQuantity', label='Sample Reference'))

    catalyst_mass = Quantity(
        type=np.float64, shape=[], unit='mg',
        a_eln=ELNAnnotation(component='NumberEditQuantity', defaultDisplayUnit='mg'))

    catalyst_density = Quantity(
        type=np.float64, shape=[], unit='g/mL',
        a_eln=ELNAnnotation(component='NumberEditQuantity', defaultDisplayUnit='g/mL'))

    apparent_catalyst_volume = Quantity(
        type=np.float64, shape=[], unit='mL',
        a_eln=ELNAnnotation(component='NumberEditQuantity', defaultDisplayUnit='mL'))

    catalyst_sievefraction_upper_limit = Quantity(
        type=np.float64, shape=[], unit='micrometer',
        a_eln=dict(component='NumberEditQuantity', defaultDisplayUnit='micrometer'))
    catalyst_sievefraction_lower_limit = Quantity(
        type=np.float64, shape=[], unit='micrometer',
        a_eln=dict(component='NumberEditQuantity', defaultDisplayUnit='micrometer'))
    particle_size = Quantity(
        type=np.float64, shape=[], unit='micrometer',
        a_eln=dict(component='NumberEditQuantity', defaultDisplayUnit='micrometer'))
    diluent = Quantity(
        type=str,
        shape=[],
        description="""
        A component that is mixed with the catalyst to dilute and prevent transport
        limitations and hot spot formation.
        """,
        a_eln=dict(component='EnumEditQuantity', props=dict(
            suggestions=['SiC', 'SiO2', 'unknown']))
    )
    diluent_sievefraction_upper_limit = Quantity(
        type=np.float64, shape=[], unit='micrometer',
        a_eln=dict(component='NumberEditQuantity', defaultDisplayUnit='micrometer'))
    diluent_sievefraction_lower_limit = Quantity(
        type=np.float64, shape=[], unit='micrometer',
        a_eln=dict(component='NumberEditQuantity', defaultDisplayUnit='micrometer'))

    def normalize(self, archive, logger):
        super().normalize(archive, logger)

        if self.sample_section_reference is None:
            if self.m_root().data.samples:
                    first_sample = self.m_root().data.samples[0]
                    if hasattr(first_sample, 'reference'):
                        self.sample_section_reference = first_sample
        # if self.sample_section_reference is not None:
        #     if self.m_root().data.samples == []:
        #         sample1_reference = CompositeSystemReference(reference=self.sample_reference)
        #         self.m_root().data.samples.append(sample1_reference)
        #     elif self.m_root().data.samples[0].reference is None:
        #         self.m_root().data.samples[0].reference = self.sample_reference
        #     self.sample_section_reference.normalize(archive, logger)

        if self.catalyst_name is None and self.sample_section_reference is not None:
            self.catalyst_name = self.sample_section_reference.name

        if (self.apparent_catalyst_volume is None and self.catalyst_mass is not None and
            self.catalyst_density is not None):
            self.apparent_catalyst_volume = self.catalyst_mass / self.catalyst_density


class CatalyticReaction_core(Measurement, ArchiveSection):

    reaction_class = Quantity(
        type=str,
        description="""
        A highlevel classification of the studied reaction.
        """,
        a_eln=dict(component='EnumEditQuantity', props=dict(suggestions=[
            'oxidation', 'hydrogenation', 'dehydrogenation', 'cracking',
            'isomerisation', 'coupling']
        )),
        links=['https://w3id.org/nfdi4cat/voc4cat_0007010'])

    reaction_name = Quantity(
        type=str,
        description="""
        The name of the studied reaction.
        """,
        a_eln=dict(
            component='EnumEditQuantity', props=dict(suggestions=[
                'ethane oxidation', 'propane oxidation',
                'butane oxidation', 'CO hydrogenation', 'methanol synthesis',
                'Fischer-Tropsch reaction', 'water gas shift reaction',
                'ammonia synthesis', 'ammonia decomposition'])),
        links=['https://w3id.org/nfdi4cat/voc4cat_0007009'])


    experiment_handbook = Quantity(
        description="""
        In case the experiment was performed according to a handbook.
        """,
        type=str,
        shape=[],
        a_eln=dict(component='FileEditQuantity'),
        links=['https://w3id.org/nfdi4cat/voc4cat_0007012']
    )

    location = Quantity(
        type=str,
        shape=[],
        description="""
        The institution at which the measurement was performed.
        """,
        a_eln=dict(component='EnumEditQuantity', props=dict(
            suggestions=['Fritz-Haber-Institut Berlin / Abteilung AC',
                         'Fritz-Haber-Institut Berlin / ISC',
                         'TU Berlin, BASCat', 'HZB', 'CATLAB']))
    )

    experimenter = Quantity(
        type=str,
        shape=[],
        description="""
        The person that performed or started the measurement.
        """,
        a_eln=dict(component='EnumEditQuantity')
    )


class SimpleCatalyticReaction(CatalyticReaction_core, EntryData):
    m_def = Section(
        label='Heterogeneous Catalysis - Simple Catalytic Reaction for measurement plugin',
        categories=[UseCaseElnCategory]
    )
    reaction_conditions = SubSection(section_def=ReactionConditionsSimple,
                                     a_eln=ELNAnnotation(label='Reaction Conditions'))
    reactor_filling = SubSection(section_def=ReactorFilling,
                                 a_eln=ELNAnnotation(label='Reactor Filling'))
    reactor_setup = SubSection(section_def=ReactorSetup,
                               a_eln=ELNAnnotation(label='Reactor Setup'))
    results = Measurement.results.m_copy()
    results.section_def = CatalyticReactionData_core
    #a_eln=ELNAnnotation(label='Reaction Results'))

    def normalize(self, archive, logger):
        super().normalize(archive, logger)

        add_activity(archive)

        if self.reaction_conditions is not None:
            if self.reaction_conditions.section_runs is not None:
                if self.reaction_conditions.section_runs[0].reagents is not None:
                    reactants=[]
                    for r in self.reaction_conditions.section_runs[0].reagents:
                        gas_concentration_in_list = np.array([])
                        for run in self.reaction_conditions.section_runs:
                            if run.reagents is not None:
                                for reagent in run.reagents:
                                    if reagent.name == r.name:
                                        if reagent.pure_component is not None:
                                            if reagent.pure_component.iupac_name is not None:
                                                r_name = reagent.pure_component.iupac_name
                                            else:
                                                r_name = reagent.name
                                        else:
                                            r_name = reagent.name
                                        gas_concentration_in_list = np.append(
                                            gas_concentration_in_list,
                                            reagent.gas_concentration_in)
                        react = Reactant_result(
                            name = r_name,
                            gas_concentration_in = gas_concentration_in_list)
                        reactants.append(react)
                archive.results.properties.catalytic.reaction.reactants = reactants
            if self.reaction_conditions.section_runs[0].gas_hourly_space_velocity is not None:
                (archive.results.properties.catalytic.reaction.
                 gas_hourly_space_velocity) = (
                 self.reaction_conditions.section_runs[0].gas_hourly_space_velocity)

        if self.results is not None and self.results != []:
            if self.results[0].reactants_conversions is not None:
                conversion_results = []
                try:
                    i_name = self.results[0].reactants_conversions.pure_component.iupac_name
                except AttributeError: #'str' object has no attribute 'pure_component':
                    try:
                        for i in self.results[0].reactants_conversions:
                            if i.pure_component is not None:
                                try:
                                    i_name = i.pure_component.iupac_name
                                except AttributeError:
                                    i_name = i.name
                            else:
                                i_name = i.name
                        conversion_result=Reactant_result(
                            name=i_name, conversion=i.conversion,
                            gas_concentration_in=i.gas_concentration_in,
                            gas_concentration_out=i.gas_concentration_out)
                        conversion_results.append(conversion_result)
                    except:
                        i_name=self.results[0].reactants_conversions.name
                finally:
                    for i in archive.results.properties.catalytic.reaction.reactants:
                        if i.name == i_name:
                            i.conversion = self.results[0].reactants_conversions.conversion
                if conversion_results != []:
                    archive.results.properties.catalytic.reaction.reactants = conversion_results
            if self.results[0].temperature is not None:
                archive.results.properties.catalytic.reaction.reaction_conditions.temperature = self.results[0].temperature
            if self.results[0].temperature is None and self.reaction_conditions.section_runs[0].set_temperature is not None:
                set_temperature = []
                for run in self.reaction_conditions.section_runs:
                    if run.set_temperature is not None:
                        set_temperature.append(run.set_temperature)
                archive.results.properties.catalytic.reaction.reaction_conditions.temperature = set_temperature
            if self.results[0].pressure is not None:
                archive.results.properties.catalytic.reaction.reaction_conditions.pressure = self.results[0].pressure
            elif self.reaction_conditions.section_runs[0].set_pressure is not None:
                set_pressure = []
                for run in self.reaction_conditions.section_runs:
                    if run.set_pressure is not None:
                        set_pressure.append(run.set_pressure)
                archive.results.properties.catalytic.reaction.reaction_conditions.pressure = set_pressure
            if self.results[0].products is not None:
                products_results=[]
                for i in self.results[0].products:
                    product_result=Product_result(name=i.name, selectivity=i.selectivity, gas_concentration_out=i.gas_concentration_out)
                    products_results.append(product_result)
                archive.results.properties.catalytic.reaction.products = products_results
        if self.reaction_name is not None:
            archive.results.properties.catalytic.reaction.name = self.reaction_name
        if self.reaction_class is not None:
            archive.results.properties.catalytic.reaction.type = self.reaction_class

        if self.samples is not None and self.samples != []:
            if self.samples[0].reference is not None:
                populate_catalyst_sample_info(archive, self, logger, reference=True)


class CatalyticReactionCleanData(CatalyticReaction_core, PlotSection, EntryData):
    """
    This schema is originally adapted to map the data of the clean Oxidation dataset (JACS,
    https://doi.org/10.1021/jacs.2c11117) The descriptions in the quantities
    represent the instructions given to the user who manually curated the data. The schema has since been extendet to match other, similar datasets, with multiple products.
    """
    m_def = Section(
        label='Heterogeneous Catalysis - Catalytic Reaction (filled by Clean Data Table)',
        a_eln=ELNAnnotation(properties=dict(order= ['name','data_file', 'reaction_name', 'reaction_class',
                            'experimenter', 'location', 'experiment_handbook'])),
        categories=[UseCaseElnCategory]
    )

    data_file = Quantity(
        type=str,
        description="""
        excel or csv file that contains results of a catalytic measurement with
        temperature, (pressure,) gas feed composition, yield, rates and selectivities
        """,
        a_eln=dict(component='FileEditQuantity'),
        a_browser=dict(adaptor='RawFileAdaptor'))

    reactor_setup = SubSection(section_def=ReactorSetup, a_eln=ELNAnnotation(label='Reactor Setup'))
    reactor_filling = SubSection(section_def=ReactorFilling, a_eln=ELNAnnotation(label='Reactor Filling'))

    reaction_conditions = SubSection(section_def=ReactionConditions, a_eln=ELNAnnotation(label='Reaction Conditions'))
    results = Measurement.results.m_copy()
    results.section_def = CatalyticReactionData
    results.a_eln = ELNAnnotation(label='Reaction Results')

    def normalize(self, archive, logger):
        super().normalize(archive, logger)
        if (self.data_file is None):
            return

        if ((self.data_file is not None) and (os.path.splitext(
                self.data_file)[-1] != ".csv" and os.path.splitext(
                self.data_file)[-1] != ".xlsx")):
            raise ValueError("Unsupported file format. Only xlsx and .csv files")

        if self.data_file.endswith(".csv"):
            with archive.m_context.raw_file(self.data_file) as f:
                import pandas as pd
                data = pd.read_csv(f.name).dropna(axis=1, how='all')
        elif self.data_file.endswith(".xlsx"):
            with archive.m_context.raw_file(self.data_file) as f:
                import pandas as pd
                data = pd.read_excel(f.name, sheet_name=0)

        data.dropna(axis=1, how='all', inplace=True)
        feed = ReactionConditions()
        reactor_filling = ReactorFilling()
        cat_data = CatalyticReactionData()
        sample = CompositeSystemReference()
        reagents = []
        reagent_names = []
        products = []
        product_names = []
        conversions = []

        conversion_names = []
        rates = []
        number_of_runs = 0
        for col in data.columns:

            if len(data[col]) < 1:
                continue
            col_split = col.split(" ")
            if len(col_split) < 2:
                continue

            if len(data[col]) > number_of_runs:
                number_of_runs = len(data[col])

            if col_split[0] == 'step':
                feed.runs = data['step']
                cat_data.runs = data['step']

            if col_split[0] == "x":
                reagent = Reagent_data(name=col_split[1], gas_concentration_in=data[col])
                reagent_names.append(col_split[1])
                reagents.append(reagent)
            if col_split[0] == "mass":
                catalyst_mass_vector = data[col]
                if '(g)' in col_split[1]:
                    reactor_filling.catalyst_mass = catalyst_mass_vector[0]*ureg.gram
                elif 'mg' in col_split[1]:
                    reactor_filling.catalyst_mass = catalyst_mass_vector[0]*ureg.milligram
            if col_split[0] == "set_temperature":
                if "K" in col_split[1]:
                    feed.set_temperature = np.nan_to_num(data[col])
                else:
                    feed.set_temperature = np.nan_to_num(data[col])*ureg.celsius
            if col_split[0] == "temperature":
                if "K" in col_split[1]:
                    cat_data.temperature = np.nan_to_num(data[col])
                else:
                    cat_data.temperature = np.nan_to_num(data[col])*ureg.celsius

            if col_split[0] == "TOS":
                cat_data.time_on_stream = data[col]
                feed.time_on_stream = data[col]

            if col_split[0] == "C-balance":
                cat_data.c_balance = np.nan_to_num(data[col])

            if col_split[0] == "GHSV":
                feed.gas_hourly_space_velocity = np.nan_to_num(data[col])

            if col_split[0] == "Vflow":
                feed.set_total_flow_rate = np.nan_to_num(data[col])

            if col_split[0] == "set_pressure":
                feed.set_pressure = np.nan_to_num(data[col])
            if col_split[0] == "pressure":
                cat_data.pressure = np.nan_to_num(data[col])

            if col_split[0] == "r":  # reaction rate
                rate = Rates(name=col_split[1], reaction_rate=np.nan_to_num(data[col]))
                # if col_split[1] in reagent_names:
                #     reactant.reaction_rate = data[col]
                # rate.reaction_rate = data[col]
                rates.append(rate)

            if len(col_split) < 3 or col_split[2] != '(%)':
                continue

            if col_split[0] == "x_p":  # conversion, based on product detection
                conversion = Reactant_data(name=col_split[1], conversion=np.nan_to_num(data[col]),
                                        conversion_type='product-based conversion', conversion_product_based=np.nan_to_num(data[col]))
                for i, p in enumerate(conversions):
                    if p.name == col_split[1]:
                        conversion = conversions.pop(i)

                conversion.conversion_product_based = np.nan_to_num(data[col])
                conversion.conversion = np.nan_to_num(data[col])
                conversion.conversion_type = 'product-based conversion'

                conversion_names.append(col_split[1])
                conversions.append(conversion)

            if col_split[0] == "x_r":  # conversion, based on reactant detection
                #if data['x '+col_split[1]+' (%)'] is not None:
                try:
                    conversion = Reactant_data(name=col_split[1], conversion=np.nan_to_num(data[col]), conversion_type='reactant-based conversion', conversion_reactant_based=np.nan_to_num(data[col]), gas_concentration_in=(np.nan_to_num(data['x '+col_split[1]+' (%)'])))
                except KeyError:
                    conversion = Reactant_data(name=col_split[1], conversion=np.nan_to_num(data[col]), conversion_type='reactant-based conversion', conversion_reactant_based=np.nan_to_num(data[col]), gas_concentration_in=np.nan_to_num(data['x '+col_split[1]])*100)
                except:
                    logger.warn('Something went wrong with reading the x_r column.')

                for i, p in enumerate(conversions):
                    if p.name == col_split[1]:
                        conversion = conversions.pop(i)
                        conversion.conversion_reactant_based = np.nan_to_num(data[col])
                conversions.append(conversion)

            if col_split[0] == "y":  # concentration out
                if col_split[1] in reagent_names:
                    conversion = Reactant_data(name=col_split[1], gas_concentration_in=np.nan_to_num(data['x '+col_split[1]+' (%)']), gas_concentration_out=np.nan_to_num(data[col]), conversion=np.nan_to_num((1-(data[col]/data['x '+col_split[1]+' (%)']))*100))
                    conversions.append(conversion)
                else:
                    product = Product_data(name=col_split[1], gas_concentration_out=np.nan_to_num(data[col]))
                    products.append(product)
                    product_names.append(col_split[1])

            if col_split[0] == "S_p":  # selectivity
                product = Product_data(name=col_split[1], selectivity=np.nan_to_num(data[col]))
                for i, p in enumerate(products):
                    if p.name == col_split[1]:
                        product = products.pop(i)
                        product.selectivity = np.nan_to_num(data[col])
                        break
                products.append(product)
                product_names.append(col_split[1])

        if 'FHI-ID' in data.columns:
            sample.lab_id = str(data['FHI-ID'][0])
        elif 'sample_id' in data.columns: # is not None:
            sample.lab_id = str(data['sample_id'][0])
        if 'catalyst' in data.columns: # is not None:
            sample.name = str(data['catalyst'][0])

        if sample != []:    #if sample information is available from data file
            from nomad.datamodel.context import ClientContext
            if isinstance(archive.m_context, ClientContext):
                pass
            else:
                sample.normalize(archive, logger)
                if self.samples is None:
                    self.samples = []
                    self.samples.append(sample)
                elif self.samples == []:
                    self.samples.append(sample)
                elif self.samples != []:
                    if self.samples[0].lab_id == sample.lab_id:
                        self.samples = []
                        self.samples.append(sample)
                    else:
                        self.samples.append(sample)
                        logger.warn('There is already a sample in the measurement. '
                                    'The sample from the data file will be added but '
                                    'sample info not written in the results section.')
        if self.samples is not None and self.samples != []:
            if self.samples[0].reference is not None:
                populate_catalyst_sample_info(archive, self, logger, reference=True)

        for reagent in reagents:
            reagent.normalize(archive, logger)
        feed.reagents = reagents

        if feed.set_total_flow_rate is not None and reactor_filling.catalyst_mass is not None:
            feed.weight_hourly_space_velocity = feed.set_total_flow_rate / reactor_filling.catalyst_mass

        if cat_data.runs is None:
            cat_data.runs = np.linspace(0, number_of_runs - 1, number_of_runs)
        cat_data.products = products
        if conversions != []:
            cat_data.reactants_conversions = conversions
        cat_data.rates = rates

        self.reaction_conditions = feed
        self.results = []
        self.results.append(cat_data)

        if self.reactor_filling is None and reactor_filling is not None:
            self.reactor_filling = reactor_filling

        self.results[0].normalize(archive, logger) #checks names of products with pubchem query

        conversions_results = []
        for i in conversions:
            if i.name in ['He', 'helium', 'Ar', 'argon', 'inert']:
                continue
            else:
                for j in reagents:
                    if i.name == j.name:
                        if j.pure_component.iupac_name is not None:
                            i.name = j.pure_component.iupac_name
                        react = Reactant_result(name=i.name, conversion=i.conversion, gas_concentration_in=i.gas_concentration_in, gas_concentration_out=i.gas_concentration_out)
                        conversions_results.append(react)
        product_results=[]
        for i in products:
            if i.pure_component is not None:
                if i.pure_component.iupac_name is not None:
                    i.name = i.pure_component.iupac_name
            prod = Product_result(name=i.name, selectivity=i.selectivity, gas_concentration_out=i.gas_concentration_out)
            product_results.append(prod)

        add_activity(archive)

        if conversions_results is not None:
            archive.results.properties.catalytic.reaction.reactants = conversions_results
        if cat_data.temperature is not None:
            archive.results.properties.catalytic.reaction.reaction_conditions.temperature = cat_data.temperature
        if cat_data.temperature is None and feed.set_temperature is not None:
            archive.results.properties.catalytic.reaction.reaction_conditions.temperature = feed.set_temperature
        if cat_data.pressure is not None:
            archive.results.properties.catalytic.reaction.reaction_conditions.pressure = cat_data.pressure
        elif feed.set_pressure is not None:
            archive.results.properties.catalytic.reaction.reaction_conditions.pressure = feed.set_pressure
        if feed.weight_hourly_space_velocity is not None:
            archive.results.properties.catalytic.reaction.reaction_conditions.weight_hourly_space_velocity = feed.weight_hourly_space_velocity
        if feed.gas_hourly_space_velocity is not None:
            archive.results.properties.catalytic.reaction.reaction_conditions.gas_hourly_space_velocity = feed.gas_hourly_space_velocity
        if products is not None:
            archive.results.properties.catalytic.reaction.products = product_results
        if self.reaction_name is not None:
            archive.results.properties.catalytic.reaction.name = self.reaction_name
            archive.results.properties.catalytic.reaction.type = self.reaction_class


        ###Figures definitions###
        self.figures = []
        if self.results[0].time_on_stream is not None:
            x=self.results[0].time_on_stream.to('hour')
            x_text="time (h)"
        elif self.results[0].runs is not None:
            x=self.results[0].runs
            x_text="steps"
        else:
            number_of_runs = len(self.reaction_conditions.set_temperature)
            x = np.linspace(0, number_of_runs - 1, number_of_runs)
            x_text = "steps"

        if self.results[0].temperature is not None:
            fig = px.line(x=x, y=self.results[0].temperature.to("celsius"))
            fig.update_xaxes(title_text=x_text)
            fig.update_yaxes(title_text="Temperature (°C)")
            self.figures.append(PlotlyFigure(label='figure Temperature', figure=fig.to_plotly_json()))
            self.results[0].figures.append(PlotlyFigure(label='Temperature', figure=fig.to_plotly_json()))

        if cat_data.pressure is not None or feed.set_pressure is not None:
            figP = go.Figure()
            if cat_data.pressure is not None:
                figP = px.line(x=x, y=cat_data.pressure.to("bar"))
            elif feed.set_pressure is not None:
                figP = px.line(x=x, y=feed.set_pressure.to("bar"))
            figP.update_xaxes(title_text=x_text)
            figP.update_yaxes(title_text="Pressure (bar)")
            self.figures.append(PlotlyFigure(label='figure Pressure', figure=figP.to_plotly_json()))

        if self.results is not None:
            if self.results[0].products is not None:
                if self.results[0].products[0].selectivity is not None:
                    fig0 = go.Figure()
                    for i,c in enumerate(self.results[0].products):
                        fig0.add_trace(go.Scatter(x=x, y=self.results[0].products[i].selectivity, name=self.results[0].products[i].name))
                    fig0.update_layout(title_text="Selectivity", showlegend=True)
                    fig0.update_xaxes(title_text=x_text)
                    fig0.update_yaxes(title_text="Selectivity (%)")
                    self.figures.append(PlotlyFigure(label='figure Selectivity', figure=fig0.to_plotly_json()))
                elif self.results[0].products[0].gas_concentration_out is not None:
                    fig0 = go.Figure()
                    for i,c in enumerate(self.results[0].products):
                        fig0.add_trace(go.Scatter(x=x, y=self.results[0].products[i].gas_concentration_out, name=self.results.products[i].name))
                    fig0.update_layout(title_text="Gas concentration out", showlegend=True)
                    fig0.update_xaxes(title_text=x_text)
                    fig0.update_yaxes(title_text="Gas concentration out (%)")
                    self.figures.append(PlotlyFigure(label='figure Gas concentration out', figure=fig0.to_plotly_json()))

        fig1 = go.Figure()
        for i,c in enumerate(self.results[0].reactants_conversions):
            fig1.add_trace(go.Scatter(x=x, y=self.results[0].reactants_conversions[i].conversion, name=self.results[0].reactants_conversions[i].name))
        fig1.update_layout(title_text="Conversion", showlegend=True)
        fig1.update_xaxes(title_text=x_text)
        fig1.update_yaxes(title_text="Conversion (%)")
        self.figures.append(PlotlyFigure(label='figure Conversion', figure=fig1.to_plotly_json()))

        if self.results[0].rates is not None:
            fig = go.Figure()
            for i,c in enumerate(self.results[0].rates):
                fig.add_trace(go.Scatter(x=x, y=self.results[0].rates[i].reaction_rate, name=self.results[0].rates[i].name))
            fig.update_layout(title_text="Rates", showlegend=True)
            fig.update_xaxes(title_text=x_text)
            fig.update_yaxes(title_text="reaction rates")
            self.results[0].figures.append(PlotlyFigure(label='Rates', figure=fig.to_plotly_json()))
            # try:
            #     fig2 = px.line(x=self.results[0].temperature.to('celsius'), y=[self.results[0].rates[0].reaction_rate])
            #     fig2.update_xaxes(title_text="Temperature (°C)")
            #     fig2.update_yaxes(title_text="reaction rate (mmol(H2)/gcat/min)")
            #     self.figures.append(PlotlyFigure(label='figure rates', figure=fig2.to_plotly_json()))
            # except:
            #     print("No rates defined")

        if self.results[0].reactants_conversions is not None and self.results[0].products is not None:
            if self.results[0].products[0].selectivity is not None:
                for i,c in enumerate(self.results[0].reactants_conversions):
                    name=self.results[0].reactants_conversions[i].name
                    fig = go.Figure()
                    for j,c in enumerate(self.results[0].products):
                        fig.add_trace(go.Scatter(x=self.results[0].reactants_conversions[i].conversion, y=self.results[0].products[j].selectivity, name=self.results[0].products[j].name, mode='markers'))
                    fig.update_layout(title_text="S-X plot "+ str(i), showlegend=True)
                    fig.update_xaxes(title_text='Conversion '+ name )
                    fig.update_yaxes(title_text='Selectivity')
                    self.figures.append(PlotlyFigure(label='S-X plot '+ name+" Conversion", figure=fig.to_plotly_json()))

        return

class CatalyticReaction(CatalyticReaction_core, PlotSection, EntryData):

    m_def = Section(
        label='Heterogeneous Catalysis - Catalytic Reaction (filled manual/ by json directly)',
        a_eln=ELNAnnotation(properties=dict(order= ['name','data_file', 'reaction_name', 'reaction_class',
                            'experimenter', 'location', 'experiment_handbook'])),
        categories=[UseCaseElnCategory]
    )

    reactor_setup = SubSection(section_def=ReactorSetup, a_eln=ELNAnnotation(label='Reactor Setup'))
    reactor_filling = SubSection(section_def=ReactorFilling, a_eln=ELNAnnotation(label='Reactor Filling'))

    pretreatment = SubSection(section_def=ReactionConditions, a_eln=ELNAnnotation(label='Pretreatment'))
    reaction_conditions = SubSection(section_def=ReactionConditions, a_eln=ELNAnnotation(label='Reaction Conditions'))
    results = Measurement.results.m_copy()
    results.section_def = CatalyticReactionData
    results.a_eln = ELNAnnotation(label='Reaction Results')
    #results = SubSection(section_def=CatalyticReactionData, a_eln=ELNAnnotation(label='Reaction Results'))

    def normalize(self, archive, logger):
        super().normalize(archive, logger)

        if self.reaction_conditions is not None:
            reagents = []
            for reagent in self.reaction_conditions.reagents:
                if reagent.pure_component is None or reagent.pure_component == []:
                    reagent.normalize(archive, logger)
                reagents.append(reagent)
            self.reaction_conditions.reagents = reagents

            if self.reaction_conditions.set_total_flow_rate is not None and self.reactor_filling.catalyst_mass is not None and self.reaction_conditions.weight_hourly_space_velocity is None:
                self.reaction_conditions.weight_hourly_space_velocity = self.reaction_conditions.set_total_flow_rate / self.reactor_filling.catalyst_mass

        if self.results is not None and self.results != []:
            self.results[0].normalize(archive, logger)
            if len(self.results) > 1:
                logger.warn('Several instances of results found. Only the first result is considered for normalization.')

            if self.results[0].reactants_conversions is not None:
                conversions_results = []
                for i in self.results[0].reactants_conversions:
                    if i.name in ['He', 'helium', 'Ar', 'argon', 'inert']:
                        continue
                    else:
                        for j in self.reaction_conditions.reagents:
                            if i.name == j.name:
                                if j.pure_component.iupac_name is not None:
                                    i.name = j.pure_component.iupac_name
                                react = Reactant_result(name=i.name, conversion=i.conversion, gas_concentration_in=i.gas_concentration_in, gas_concentration_out=i.gas_concentration_out)
                                conversions_results.append(react)

            product_results=[]
            if self.results[0].products is not None:
                for i in self.results[0].products:
                    if i.pure_component is not None:
                        if i.pure_component.iupac_name is not None:
                            i.name = i.pure_component.iupac_name
                    prod = Product_result(name=i.name, selectivity=i.selectivity, gas_concentration_out=i.gas_concentration_out)
                    product_results.append(prod)

        add_activity(archive)

        try:
            if conversions_results is not None:
                archive.results.properties.catalytic.reaction.reactants = conversions_results
        except UnboundLocalError:
            pass
        if self.results is not None and self.results != []:
            if self.results[0].temperature is not None:
                archive.results.properties.catalytic.reaction.reaction_conditions.temperature = self.results[0].temperature
            elif self.reaction_conditions.set_temperature is not None:
                archive.results.properties.catalytic.reaction.reaction_conditions.temperature = self.reaction_conditions.set_temperature
            if self.results[0].pressure is not None:
                archive.results.properties.catalytic.reaction.reaction_conditions.pressure = self.results[0].pressure
            elif self.reaction_conditions.set_pressure is not None:
                archive.results.properties.catalytic.reaction.reaction_conditions.pressure = self.reaction_conditions.set_pressure
            if product_results is not None and product_results != []:
                archive.results.properties.catalytic.reaction.products = product_results
        if self.reaction_conditions is not None:
            if self.reaction_conditions.weight_hourly_space_velocity is not None:
                archive.results.properties.catalytic.reaction.reaction_conditions.weight_hourly_space_velocity = self.reaction_conditions.weight_hourly_space_velocity
            if self.reaction_conditions.gas_hourly_space_velocity is not None:
                archive.results.properties.catalytic.reaction.reaction_conditions.gas_hourly_space_velocity = self.reaction_conditions.gas_hourly_space_velocity
        if self.reaction_name is not None:
            archive.results.properties.catalytic.reaction.name = self.reaction_name
        if self.reaction_class is not None:
            archive.results.properties.catalytic.reaction.type = self.reaction_class

        if self.samples is not None and self.samples != []:
            if self.samples[0].lab_id is not None and self.samples[0].reference is None:
                sample = CompositeSystemReference(lab_id=self.samples[0].lab_id, name=self.samples[0].name)
                sample.normalize(archive, logger)
                self.samples = []
                self.samples.append(sample)
            if self.samples[0].reference is not None:
                populate_catalyst_sample_info(archive, self, logger, reference=True)

        if self.results is None or self.results == []:
            return

        ###Figures definitions###
        self.figures = []
        if self.results[0].time_on_stream is not None:
            x=self.results[0].time_on_stream.to('hour')
            x_text="time (h)"
        elif self.results[0].runs is not None:
            x=self.results[0].runs
            x_text="steps"
        else:
            number_of_runs = len(self.reaction_conditions.set_temperature)
            x = np.linspace(1, number_of_runs, number_of_runs)
            x_text = "steps"

        if self.results[0].temperature is not None or self.reaction_conditions.set_temperature is not None:
            fig = go.Figure()
            if self.results[0].temperature is not None and self.results[0].temperature !=[]:
                fig = px.line(x=x, y=self.results[0].temperature.to("celsius"), markers=True)
            elif self.reaction_conditions.set_temperature is not None:
                fig = px.line(x=x, y=self.reaction_conditions.set_temperature.to("celsius"), markers=True)
            fig.update_xaxes(title_text=x_text)
            fig.update_yaxes(title_text="Temperature (°C)")
            self.figures.append(PlotlyFigure(label='figure Temperature', figure=fig.to_plotly_json()))

        if self.results[0].pressure is not None or self.reaction_conditions.set_pressure is not None:
            figP = go.Figure()
            if self.results[0].pressure is not None:
                figP = px.line(x=x, y=self.results[0].pressure.to("bar"), markers=True)
            elif self.reaction_conditions.set_pressure is not None:
                figP = px.line(x=x, y=self.reaction_conditions.set_pressure.to("bar"), markers=True)
            figP.update_xaxes(title_text=x_text)
            figP.update_yaxes(title_text="Pressure (bar)")
            self.figures.append(PlotlyFigure(label='figure Pressure', figure=figP.to_plotly_json()))

        fig0 = go.Figure()
        for i,c in enumerate(self.results[0].products):
            fig0.add_trace(go.Scatter(x=x, y=self.results[0].products[i].selectivity, name=self.results[0].products[i].name))
        fig0.update_layout(title_text="Selectivity", showlegend=True)
        fig0.update_xaxes(title_text="measurement points")
        fig0.update_yaxes(title_text="Selectivity (%)")
        self.figures.append(PlotlyFigure(label='figure Selectivity', figure=fig0.to_plotly_json()))

        fig1 = go.Figure()
        for i,c in enumerate(self.results[0].reactants_conversions):
            fig1.add_trace(go.Scatter(x=x, y=self.results[0].reactants_conversions[i].conversion, name=self.results[0].reactants_conversions[i].name))
        fig1.update_layout(title_text="Conversion", showlegend=True)
        fig1.update_xaxes(title_text=x_text)
        fig1.update_yaxes(title_text="Conversion (%)")
        self.figures.append(PlotlyFigure(label='figure Conversion', figure=fig1.to_plotly_json()))

        if self.results[0].rates is not None:
            fig = go.Figure()
            for i,c in enumerate(self.results[0].rates):
                fig.add_trace(go.Scatter(x=x, y=self.results[0].rates[i].rate, name=self.results[0].rates[i].name))
            fig.update_layout(title_text="Rates", showlegend=True)
            fig.update_xaxes(title_text=x_text)
            fig.update_yaxes(title_text="rates (g product/g cat/h)")
            self.figures.append(PlotlyFigure(label='Rates', figure=fig.to_plotly_json()))
            # try:
            #     fig2 = px.line(x=self.results[0].temperature.to('celsius'), y=[self.results[0].rates[0].reaction_rate])
            #     fig2.update_xaxes(title_text="Temperature (°C)")
            #     fig2.update_yaxes(title_text="reaction rate (mmol(H2)/gcat/min)")
            #     self.figures.append(PlotlyFigure(label='figure rates', figure=fig2.to_plotly_json()))
            # except:
            #     print("No rates defined")

        for i,c in enumerate(self.results[0].reactants_conversions):
                name=self.results[0].reactants_conversions[i].name
                fig = go.Figure()
                for j,c in enumerate(self.results[0].products):
                    fig.add_trace(go.Scatter(x=self.results[0].reactants_conversions[i].conversion, y=self.results[0].products[j].selectivity, name=self.results[0].products[j].name, mode='markers'))
                fig.update_layout(title_text="S-X plot "+ str(i), showlegend=True)
                fig.update_xaxes(title_text='Conversion '+ name )
                fig.update_yaxes(title_text='Selectivity (%)')
                self.figures.append(PlotlyFigure(label='S-X plot '+ name+" Conversion", figure=fig.to_plotly_json()))

        return


class CatalyticReaction_NH3decomposition(CatalyticReaction_core, PlotSection, EntryData):
    m_def = Section(
        label='Heterogeneous Catalysis - Catalytic Reaction NH3 Decomposition (filled by h5 file from Haber)',
        a_eln=ELNAnnotation(properties=dict(order= ['name','data_file_h5', 'reaction_name','reaction_class',
                            'experimenter', 'location', 'experiment_handbook'])),
        categories=[UseCaseElnCategory],
    )

    data_file_h5 = Quantity(
        type=str,
        description="""
        hdf5 file that contains 'Sorted Data' of a catalytic measurement with
        time, temperature,  Conversion, Space_time_Yield
        """,
        a_eln=dict(component='FileEditQuantity'),
        a_browser=dict(adaptor='RawFileAdaptor')
    )

    reactor_setup = SubSection(section_def=ReactorSetup, a_eln=ELNAnnotation(label='Reactor Setup'))
    reactor_filling = SubSection(section_def=ReactorFilling, a_eln=ELNAnnotation(label='Reactor Filling'))

    pretreatment = SubSection(section_def=ReactionConditions)
    reaction_conditions = SubSection(section_def=ReactionConditions, a_eln=ELNAnnotation(label='Reaction Conditions'))
    results = Measurement.results.m_copy()
    results.section_def = CatalyticReactionData_core
    results.a_eln = ELNAnnotation(label='Reaction Results')

    def normalize(self, archive, logger):
        super(CatalyticReaction_NH3decomposition, self).normalize(archive, logger)

        if self.data_file_h5 is None:
            return

        if (self.data_file_h5 is not None) and (os.path.splitext(
                self.data_file_h5)[-1] != ".h5"):
            raise ValueError("Unsupported file format. This should be a hdf5 file ending with '.h5'" )
            return

        if self.data_file_h5.endswith(".h5"):
            with archive.m_context.raw_file(self.data_file_h5) as f:
                import h5py
                data = h5py.File(f.name, 'r')

        cat_data=CatalyticReactionData_core()
        feed=ReactionConditions()
        reactor_setup=ReactorSetup()
        reactor_filling=ReactorFilling()
        pretreatment=ReactionConditions()
        sample=CompositeSystemReference()
        conversions=[]
        conversions2=[]
        rates=[]
        reagents=[]
        pre_reagents=[]
        time_on_stream=[]
        time_on_stream_reaction=[]
        method=list(data['Sorted Data'].keys())
        for i in method:
            methodname=i
        header=data["Header"][methodname]["Header"]
        reactor_filling.catalyst_mass = header["Catalyst Mass [mg]"]/1000
        feed.sampling_frequency = header["Temporal resolution [Hz]"]*ureg.hertz
        reactor_setup.name = 'Haber'
        reactor_setup.reactor_type = 'plug flow reactor'
        reactor_setup.reactor_volume = header["Bulk volume [mln]"]
        reactor_setup.reactor_cross_section_area = (header['Inner diameter of reactor (D) [mm]']/2)**2 * np.pi
        reactor_setup.reactor_diameter = header['Inner diameter of reactor (D) [mm]']
        reactor_filling.diluent = header['Diluent material'][0].decode()
        reactor_filling.diluent_sievefraction_upper_limit = header['Diluent Sieve fraction high [um]']
        reactor_filling.diluent_sievefraction_lower_limit = header['Diluent Sieve fraction low [um]']
        reactor_filling.catalyst_mass = header['Catalyst Mass [mg]'][0]*ureg.milligram
        reactor_filling.catalyst_sievefraction_upper_limit = header['Sieve fraction high [um]']
        reactor_filling.catalyst_sievefraction_lower_limit = header['Sieve fraction low [um]']
        reactor_filling.particle_size = header['Particle size (Dp) [mm]']

        self.experimenter = header['User'][0].decode()

        pre=data["Sorted Data"][methodname]["H2 Reduction"]
        pretreatment.set_temperature = pre["Catalyst Temperature [C°]"]*ureg.celsius
        for col in pre.dtype.names :
            if col == 'Massflow3 (H2) Target Calculated Realtime Value [mln|min]':
                pre_reagent = Reagent_data(name='hydrogen', flow_rate=pre[col])
                pre_reagents.append(pre_reagent)
            if col == 'Massflow5 (Ar) Target Calculated Realtime Value [mln|min]':
                pre_reagent = Reagent_data(name='argon', flow_rate=pre[col])
                pre_reagents.append(pre_reagent)
            # if col.startswith('Massflow'):
            #     col_split = col.split("(")
            #     col_split1 = col_split[1].split(")")
            #     if col_split1[1].startswith(' actual'):
            #         reagent = Reagent(name=col_split1[0], flow_rate=pre[col])
            #         pre_reagents.append(reagent)
        pretreatment.reagents = pre_reagents
        pretreatment.set_total_flow_rate = pre['Target Total Gas (After Reactor) [mln|min]']
        number_of_runs = len(pre["Catalyst Temperature [C°]"])
        pretreatment.runs = np.linspace(0, number_of_runs - 1, number_of_runs)

        time=pre['Relative Time [Seconds]']
        for i in range(len(time)):
            t = float(time[i].decode("UTF-8"))-float(time[0].decode("UTF-8"))
            time_on_stream.append(t)
        pretreatment.time_on_stream = time_on_stream*ureg.sec

        analysed=data["Sorted Data"][methodname]["NH3 Decomposition"]

        for col in analysed.dtype.names :
            if col.endswith('Target Calculated Realtime Value [mln|min]'):
                name_split=col.split("(")
                gas_name=name_split[1].split(")")
                if 'NH3' in gas_name:
                    reagent = Reagent_data(name='NH3', flow_rate=analysed[col])
                    reagents.append(reagent)
                else:
                    reagent = Reagent_data(name=gas_name[0], flow_rate=analysed[col])
                    reagents.append(reagent)
        feed.reagents = reagents
        # feed.flow_rates_total = analysed['MassFlow (Total Gas) [mln|min]']
        conversion = Reactant_data(name='ammonia', conversion=np.nan_to_num(analysed['NH3 Conversion [%]']))
        conversions.append(conversion)
        #reducing array size for results section:
        if len(analysed['NH3 Conversion [%]']) > 50:
            conversion2 = Reactant_result(name='ammonia', conversion=analysed['NH3 Conversion [%]'][50::100], gas_concentration_in=[100]*len(analysed['NH3 Conversion [%]'][50::100]))
        else:
            conversion2 = Reactant_result(name='ammonia', conversion=analysed['NH3 Conversion [%]'], gas_concentration_in=[100]*len(analysed['NH3 Conversion [%]']))
        conversions2.append(conversion2)
        rate = Rates(name='molecular hydrogen', reaction_rate=np.nan_to_num(analysed['Space Time Yield [mmolH2 gcat-1 min-1]']*ureg.mmol/ureg.g/ureg.minute))
        rates.append(rate)
        feed.set_temperature = analysed['Catalyst Temperature [C°]']*ureg.celsius
        cat_data.temperature = analysed['Catalyst Temperature [C°]']*ureg.celsius
        number_of_runs = len(analysed['NH3 Conversion [%]'])
        feed.runs = np.linspace(0, number_of_runs - 1, number_of_runs)
        cat_data.runs = np.linspace(0, number_of_runs - 1, number_of_runs)
        time=analysed['Relative Time [Seconds]']
        for i in range(len(time)):
            t = float(time[i].decode("UTF-8"))-float(time[0].decode("UTF-8"))
            time_on_stream_reaction.append(t)
        cat_data.time_on_stream = time_on_stream_reaction*ureg.sec

        cat_data.reactants_conversions = conversions
        cat_data.rates = rates

        self.method = methodname
        self.datetime = pre['Date'][0].decode()

        sample.name = 'catalyst'
        sample.lab_id = str(data["Header"]["Header"]['SampleID'][0])
        sample.normalize(archive, logger)

        self.results.append(cat_data)
        self.reaction_conditions = feed
        self.reactor_setup = reactor_setup
        self.pretreatment=pretreatment
        self.reactor_filling=reactor_filling

        self.samples.append(sample)

        products_results = []
        for i in ['molecular nitrogen', 'molecular hydrogen']:
            product = Product_result(name=i)
            products_results.append(product)
        self.products = products_results

        add_activity(archive)
        #reduce the size of the arrays for results section:
        if len(cat_data.temperature) > 50:
            temp_results = cat_data.temperature[50::100]

        if self.reaction_conditions.set_pressure is None and self.results[0].pressure is None:
            archive.results.properties.catalytic.reaction.pressure = [1.0]*ureg.bar
        if conversions2 is not None:
            archive.results.properties.catalytic.reaction.reactants = conversions2
        if cat_data.temperature is not None:
            archive.results.properties.catalytic.reaction.reaction_conditions.temperature = temp_results
        if cat_data.pressure is not None:
            archive.results.properties.catalytic.reaction.reaction_conditions.pressure = cat_data.pressure
        if products_results != []:
            archive.results.properties.catalytic.reaction.products = products_results
        if rates is not None:
            archive.results.properties.catalytic.reaction.rates = rates
        if self.reaction_name is None:
            self.reaction_name = 'ammonia decomposition'
            self.reaction_class = 'cracking'
        archive.results.properties.catalytic.reaction.name = self.reaction_name
        archive.results.properties.catalytic.reaction.type = self.reaction_class

        if self.samples is not None and self.samples != []:
            if self.samples[0].reference is not None:
                populate_catalyst_sample_info(archive, self, logger, reference=True)

        self.figures = []
        fig = px.line(x=self.results[0].time_on_stream, y=self.results[0].temperature.to('celsius'))
        fig.update_xaxes(title_text="time(h)")
        fig.update_yaxes(title_text="Temperature (°C)")
        self.figures.append(PlotlyFigure(label='figure Temp', figure=fig.to_plotly_json()))

        for i,c in enumerate(self.results[0].reactants_conversions):
            fig1 = px.line(x=self.results[0].time_on_stream, y=[self.results[0].reactants_conversions[i].conversion])
            fig1.update_layout(title_text="Conversion")
            fig1.update_xaxes(title_text="time(h)")
            fig1.update_yaxes(title_text="Conversion (%)")
            self.figures.append(PlotlyFigure(label='figure Conversion', figure=fig1.to_plotly_json()))

        fig2 = px.line(x=self.results[0].temperature.to('celsius'), y=[self.results[0].rates[0].reaction_rate])
        fig2.update_xaxes(title_text="Temperature (°C)")
        fig2.update_yaxes(title_text="reaction rate (mmol(H2)/gcat/min)")
        self.figures.append(PlotlyFigure(label='figure rates', figure=fig2.to_plotly_json()))

        fig3 = px.scatter(x=self.pretreatment.runs, y=self.pretreatment.set_temperature.to('celsius'))
        fig3.update_layout(title_text="Pretreatment Temperature Program")
        fig3.update_xaxes(title_text="measurement points",)
        fig3.update_yaxes(title_text="Temperature (°C)")
        self.pretreatment.figures.append(PlotlyFigure(label='Temperature', figure=fig3.to_plotly_json()))

        fig4 = px.scatter(x=self.reaction_conditions.runs, y=self.reaction_conditions.set_temperature.to('celsius'))
        fig4.update_layout(title_text="Temperature Program")
        fig4.update_xaxes(title_text="measurement points",)
        fig4.update_yaxes(title_text="Temperature (°C)")
        self.reaction_conditions.figures.append(PlotlyFigure(label='Temperature', figure=fig4.to_plotly_json()))

m_package.__init_metainfo__()
