#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD. See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import numpy as np
import os
from nomad.units import ureg
from ase.data import chemical_symbols

from nomad.datamodel.metainfo.basesections import (
    CompositeSystem,
    CompositeSystemReference,
    PubChemPureSubstanceSection)

from typing import (
    TYPE_CHECKING,
)
from nomad.datamodel.results import (Results, Material, Properties, CatalyticProperties,
                                     CatalystCharacterization, CatalystSynthesis, Reaction,
                                    Reactant as Reactant_result,
                                    Product as Product_result)
from nomad.metainfo import (
    Package,
    Quantity,
    SubSection,
    Section,
)
from nomad.datamodel.metainfo.plot import PlotSection, PlotlyFigure
import plotly.express as px
import plotly.graph_objs as go
from nomad.datamodel.metainfo.annotations import ELNAnnotation
from nomad.datamodel.data import (
    EntryData,
    ArchiveSection,
)
if TYPE_CHECKING:
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )
    from structlog.stdlib import (
        BoundLogger,
    )

m_package = Package(name='A schema for catalyst tests')

def add_catalyst(archive):
    '''Adds metainfo structure for catalysis data.'''
    if not archive.results:
        archive.results = Results()
    if not archive.results.properties:
        archive.results.properties = Properties()
    if not archive.results.properties.catalytic:
        archive.results.properties.catalytic = CatalyticProperties()
    if not archive.results.properties.catalytic.catalyst_characterization:
        archive.results.properties.catalytic.catalyst_characterization = CatalystCharacterization()
    if not archive.results.properties.catalytic.catalyst_synthesis:
        archive.results.properties.catalytic.catalyst_synthesis = CatalystSynthesis()

def populate_catalyst_sampleinfo(archive, self, logger):
    '''
    Copies the catalyst sample information from a reference into the results archive of the measurement.
    '''
    if self.samples is not None and self.samples != []:
        if self.samples[0].reference is not None:
            add_catalyst(archive)

            if self.samples[0].reference.name is not None:
                archive.results.properties.catalytic.catalyst_synthesis.catalyst_name = self.samples[0].reference.name
                if not archive.results.material:
                    archive.results.material = Material()
                archive.results.material.material_name = self.samples[0].reference.name
            if self.samples[0].reference.catalyst_type is not None:
                archive.results.properties.catalytic.catalyst_synthesis.catalyst_type = self.samples[0].reference.catalyst_type
            if self.samples[0].reference.preparation_details is not None:
                archive.results.properties.catalytic.catalyst_synthesis.preparation_method = self.samples[0].reference.preparation_details.preparation_method
            if self.samples[0].reference.surface is not None:
                archive.results.properties.catalytic.catalyst_characterization.surface_area = self.samples[0].reference.surface.surface_area

            if self.samples[0].reference.elemental_composition is not None:
                if not archive.results.material:
                    archive.results.material = Material()

            try:
                archive.results.material.elemental_composition = self.samples[0].reference.elemental_composition

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

def add_activity(archive):
    '''Adds metainfo structure for catalysis activity test data.'''
    if not archive.results:
        archive.results = Results()
    if not archive.results.properties:
        archive.results.properties = Properties()
    if not archive.results.properties.catalytic:
        archive.results.properties.catalytic = CatalyticProperties()
    if not archive.results.properties.catalytic.reaction:
        archive.results.properties.catalytic.reaction = Reaction()

class Reagent(ArchiveSection):
    m_def = Section(label_quantity='name',
                    description='a chemical substance present in the initial reaction mixture')
    name = Quantity(type=str,
                    a_eln=ELNAnnotation(label='reagent name',
                        component='StringEditQuantity'),
                    description="reagent name")
    gas_concentration_in = Quantity(
        type=np.float64, shape=['*'],
        description='Volumetric fraction of reactant in feed.',
        a_eln=ELNAnnotation(component='NumberEditQuantity'))
    flow_rate = Quantity(
        type=np.float64, shape=['*'], unit='mL/minutes',
        description='Flow rate of reactant in feed.',
        a_eln=ELNAnnotation(component='NumberEditQuantity'))

    pure_component = SubSection(section_def=PubChemPureSubstanceSection)

    def normalize(self, archive, logger):
        '''
        The normalizer for the `PureSubstanceComponent` class. If none is set, the
        normalizer will set the name of the component to be the molecular formula of the
        substance.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger ('BoundLogger'): A structlog logger.
        '''
        super(Reagent, self).normalize(archive, logger)

        if self.name is None:
            return
        if self.name in ['C5-1', 'C6-1', 'nC5', 'nC6','Unknown','inert','P>=5C']:
            return
        elif self.name == 'n-Butene':
            self.name = '1-butene'
        elif self.name == 'MAN':
            self.name = 'maleic anhydride'
        elif '_' in self.name:
            self.name = self.name.replace('_',' ')
        if self.name and self.pure_component is None:
            import time
            self.pure_component = PubChemPureSubstanceSection(
                name=self.name
            )
            time.sleep(1)
            self.pure_component.normalize(archive, logger)

        if self.pure_component is not None and self.pure_component.iupac_name is None:
            if self.pure_component.molecular_formula == 'CO2':
                self.pure_component.iupac_name = 'carbon dioxide'

        if self.name == "CO" or self.name == "carbon monoxide":
            self.pure_component.iupac_name = 'carbon monoxide'
            self.pure_component.molecular_formula = 'CO'
            self.pure_component.molecular_mass = 28.01
            self.pure_component.inchi = 'InChI=1S/CO/c1-2'
            self.pure_component.inchi_key = 'UGFAIRIUMAVXCW-UHFFFAOYSA-N'
            self.pure_component.cas_number = '630-08-0'

        if self.name is None and self.pure_component is not None:
            self.name = self.pure_component.molecular_formula


class Reactant(Reagent):
    m_def = Section(label_quantity='name', description='A reagent that has a conversion in a reaction that is not null')

    gas_concentration_out = Quantity(
        type=np.float64, shape=['*'],
        description='Volumetric fraction of reactant in outlet.',
        a_eln=ELNAnnotation(component='NumberEditQuantity'))

    reference = Quantity(type=Reagent, a_eln=dict(component='ReferenceEditQuantity'))
    conversion = Quantity(type=np.float64, shape=['*'])
    conversion_type = Quantity(type=str, a_eln=dict(component='StringEditQuantity', props=dict(
        suggestions=['product_based', 'reactant_based', 'unknown'])))
    conversion_product_based = Quantity(type=np.float64, shape=['*'])
    conversion_reactant_based = Quantity(type=np.float64, shape=['*'])

class ReactionConditions(PlotSection, ArchiveSection):
    m_def = Section(description='A class containing reaction conditions for a generic reaction.')

    set_temperature = Quantity(
        type=np.float64, shape=['*'], unit='K', a_eln=ELNAnnotation(component='NumberEditQuantity'))

    set_pressure = Quantity(
        type=np.float64, shape=['*'], unit='bar', a_eln=ELNAnnotation(component='NumberEditQuantity', defaultDisplayUnit='bar'))

    set_total_flow_rate = Quantity(
        type=np.float64, shape=['*'], unit='mL/minute', a_eln=ELNAnnotation(component='NumberEditQuantity'))

    weight_hourly_space_velocity = Quantity(
        type=np.float64, shape=['*'], unit='mL/(g*hour)', a_eln=dict(component='NumberEditQuantity'))

    contact_time = Quantity(
        type=np.float64, shape=['*'], unit='g*s/mL', a_eln=ELNAnnotation(label='W|F'))

    gas_hourly_space_velocity = Quantity(
        type=np.float64, shape=['*'], unit='1/hour', a_eln=dict(component='NumberEditQuantity'))

    runs = Quantity(type=np.float64, shape=['*'])

    sampling_frequency = Quantity(  #maybe better use sampling interval?
        type=np.float64, shape=[], unit='Hz',
        description='The number of measurement points per time.',
        a_eln=dict(component='NumberEditQuantity'))

    time_on_stream = Quantity(
        type=np.float64, shape=['*'], unit='hour', a_eln=dict(component='NumberEditQuantity', defaultDisplayUnit='hour'))

    reagents = SubSection(section_def=Reagent, repeats=True)

class Rates(ArchiveSection):
    m_def = Section(label_quantity='name')
    name = Quantity(type=str, a_eln=ELNAnnotation(component='StringEditQuantity'))

    reaction_rate = Quantity(
        type=np.float64,
        shape=['*'],
        unit='mmol/g/hour',
        description='The reaction rate for mmol of product (or reactant) formed (depleted) per catalyst (g) per time (hour).')
    specific_mass_rate = Quantity(
        type=np.float64, shape=['*'], unit='mmol/g/hour',
        description='The specific reaction rate normalized by active (metal) catalyst mass, instead of mass of total catalyst.')
    specific_surface_area_rate = Quantity(
        type=np.float64, shape=['*'], unit='mmol/m**2/hour',
        description='The specific reaction rate normalized by active (metal) surface area of catalyst, instead of mass of total catalyst.')
    space_time_yield = Quantity(
        type=np.float64,
        shape=['*'],
        unit='g/g/hour',
        description='The amount of product formed (in g), per total catalyst (g) per time (hour).')
    rate = Quantity(
        type=np.float64, shape=['*'], unit='g/g/hour',
        description='The amount of reactant converted (in g), per total catalyst (g) per time (hour).'
    )
    turn_over_frequency = Quantity(
        type=np.float64, shape=['*'], unit='1/hour',
        description='The turn oder frequency, calculated from mol of reactant or product, per number of sites, over time.')


class Product(Reagent, ArchiveSection):
    m_def = Section(label_quantity='name', description='a chemical substance formed in the reaction mixture during a reaction')

    gas_concentration_out = Quantity(
        type=np.float64, shape=['*'],
        description='Volumetric fraction of reactant in outlet.',
        a_eln=ELNAnnotation(component='NumberEditQuantity'))

    selectivity = Quantity(
        type=np.float64, shape=['*'],
        description='The selectivity of the product in the reaction mixture.',
        a_eln=ELNAnnotation(component='NumberEditQuantity'),
        iris=['https://w3id.org/nfdi4cat/voc4cat_0000125'])

    product_yield = Quantity(type=np.float64, shape=['*'],
                             description='The yield of the product in the reaction mixture, calculated as conversion x selectivity.',
                             a_eln=ELNAnnotation(component='NumberEditQuantity'))

    rates = SubSection(section_def=Rates)

    def normalize(self, archive, logger):
        '''
        The normalizer for the adjusted `PureSubstanceComponent` class. If none is set, the
        normalizer will set the name of the component to be the molecular formula of the
        substance.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger ('BoundLogger'): A structlog logger.
        '''
        super(Product, self).normalize(archive, logger)

class ReactorSetup(ArchiveSection):
    m_def = Section(label_quantity='name')
    name = Quantity(type=str, shape=[], a_eln=dict(component='EnumEditQuantity'))
    reactor_type = Quantity(type=str, shape=[], a_eln=dict(component='EnumEditQuantity'),
                             props=dict(suggestions=['plug flow reactor', 'batch reactor', 'continuous stirred-tank reactor', 'fluidized bed']))
    bed_length = Quantity(type=np.float64, shape=[], unit='mm',
                          a_eln=dict(component='NumberEditQuantity'))
    reactor_cross_section_area = Quantity(type=np.float64, shape=[], unit='mm**2',
                                          a_eln=dict(component='NumberEditQuantity'))
    reactor_diameter = Quantity(type=np.float64, shape=[], unit='mm',
                                          a_eln=dict(component='NumberEditQuantity'))
    reactor_volume = Quantity(type=np.float64, shape=[], unit='ml',
                              a_eln=dict(component='NumberEditQuantity'))


class CatalyticReactionData_core(ArchiveSection):
    temperature = Quantity(
        type=np.float64, shape=['*'], unit='°C', a_eln=ELNAnnotation(component='NumberEditQuantity'))

    pressure = Quantity(
        type=np.float64, shape=['*'], unit='bar', a_eln=ELNAnnotation(component='NumberEditQuantity'))

    runs = Quantity(type=np.float64, shape=['*'], a_eln=ELNAnnotation(component='NumberEditQuantity'))
    time_on_stream = Quantity(type=np.float64, shape=['*'], unit='hour', a_eln=ELNAnnotation(component='NumberEditQuantity'))

    reactants_conversions = SubSection(section_def=Reactant, repeats=True)
    rates = SubSection(section_def=Rates, repeats=True)

    products = SubSection(section_def=Product, repeats=True)

    def normalize(self, archive, logger):

        if self.products is not None:
            for product in self.products:
                if product.pure_component is None or product.pure_component == []:
                    product.normalize(archive, logger)


class ReactorFilling(ArchiveSection):
    m_def = Section(description='A class containing information about the catalyst and filling in the reactor.',
                    label='Catalyst')

    catalyst_name = Quantity(
        type=str, shape=[], a_eln=ELNAnnotation(component='StringEditQuantity'))

    sample_reference = Quantity(
        type=CompositeSystem, description='A reference to the sample used for the measurement.',
        a_eln=ELNAnnotation(component='ReferenceEditQuantity', label='Entity Reference'))

    catalyst_mass = Quantity(
        type=np.float64, shape=[], unit='mg', a_eln=ELNAnnotation(component='NumberEditQuantity'))

    catalyst_density = Quantity(
        type=np.float64, shape=[], unit='g/mL', a_eln=ELNAnnotation(component='NumberEditQuantity'))

    apparent_catalyst_volume = Quantity(
        type=np.float64, shape=[], unit='mL', a_eln=ELNAnnotation(component='NumberEditQuantity'))

    catalyst_sievefraction_upper_limit = Quantity(
        type=np.float64, shape=[], unit='micrometer',
        a_eln=dict(component='NumberEditQuantity'))
    catalyst_sievefraction_lower_limit = Quantity(
        type=np.float64, shape=[], unit='micrometer',
        a_eln=dict(component='NumberEditQuantity'))
    particle_size = Quantity(
        type=np.float64, shape=[], unit='micrometer',
        a_eln=dict(component='NumberEditQuantity'))
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
        a_eln=dict(component='NumberEditQuantity'))
    diluent_sievefraction_lower_limit = Quantity(
        type=np.float64, shape=[], unit='micrometer',
        a_eln=dict(component='NumberEditQuantity'))

    def normalize(self, archive, logger):
        super(ReactorFilling, self).normalize(archive, logger)

        if self.sample_reference is None:
            if self.m_root().data.samples != []:
                if self.m_root().data.samples[0].reference is not None:
                    self.sample_reference = self.m_root().data.samples[0].reference
        if self.sample_reference is not None:
            if self.m_root().data.samples == []:
                sample1_reference = CompositeSystemReference(reference=self.sample_reference)
                self.m_root().data.samples.append(sample1_reference)
            elif self.m_root().data.samples[0].reference is None:
                self.m_root().data.samples[0].reference = self.sample_reference
            self.sample_reference.normalize(archive, logger)

        if self.catalyst_name is None and self.sample_reference is not None:
            self.catalyst_name = self.sample_reference.name

        if self.apparent_catalyst_volume is None and self.catalyst_mass is not None and self.catalyst_density is not None:
            self.apparent_catalyst_volume = self.catalyst_mass / self.catalyst_density


class CatalyticReactionData(PlotSection, CatalyticReactionData_core, ArchiveSection):

    c_balance = Quantity(
        type=np.dtype(
            np.float64), shape=['*'], a_eln=ELNAnnotation(component='NumberEditQuantity'))


class CatalystTests(CompositeSystem, EntryData, ArchiveSection):
    '''
    Class autogenerated from yaml schema.
    '''
    m_def = Section()
    name = Quantity(
        type=str,
        a_eln={
            "component": "StringEditQuantity"
        },
    )
    data_file = Quantity(
        type=str,
        a_eln={
            "component": "FileEditQuantity"
        },
        a_browser=dict(adaptor='RawFileAdaptor')
    )
    reaction_class = Quantity(
        type=str,
        a_eln={
            "component": "StringEditQuantity"
        },
    )
    location = Quantity(
        type=str,
        a_eln={
            "component": "StringEditQuantity"
        },
    )
    reaction_name = Quantity(
        type=str,
        a_eln={
            "component": "StringEditQuantity"
        },
    )
    experimenter = Quantity(
        type=str,
        a_eln={
            "component": "StringEditQuantity"
        },
    )
    samples = SubSection(
        section_def=CompositeSystemReference,
        repeats=True,
    )

    reactor_setup = SubSection(section_def=ReactorSetup)
    reactor_filling = SubSection(section_def=ReactorFilling)

    reaction_conditions = SubSection(section_def=ReactionConditions, a_eln=ELNAnnotation(label='Reaction Conditions'))
    reaction_results = SubSection(section_def=CatalyticReactionData, a_eln=ELNAnnotation(label='Reaction Results'))


    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        '''
        The normalizer for the `CatalystTests` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        '''

        super(CatalystTests, self).normalize(archive, logger)
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
                reagent = Reagent(name=col_split[1], gas_concentration_in=data[col])
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
                conversion = Reactant(name=col_split[1], conversion=np.nan_to_num(data[col]),
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
                    conversion = Reactant(name=col_split[1], conversion=np.nan_to_num(data[col]), conversion_type='reactant-based conversion', conversion_reactant_based=np.nan_to_num(data[col]), gas_concentration_in=(np.nan_to_num(data['x '+col_split[1]+' (%)'])))
                except KeyError:
                    conversion = Reactant(name=col_split[1], conversion=np.nan_to_num(data[col]), conversion_type='reactant-based conversion', conversion_reactant_based=np.nan_to_num(data[col]), gas_concentration_in=np.nan_to_num(data['x '+col_split[1]])*100)
                except:
                    logger.warn('Something went wrong with reading the x_r column.')

                for i, p in enumerate(conversions):
                    if p.name == col_split[1]:
                        conversion = conversions.pop(i)
                        conversion.conversion_reactant_based = np.nan_to_num(data[col])
                conversions.append(conversion)

            if col_split[0] == "y":  # concentration out
                if col_split[1] in reagent_names:
                    conversion = Reactant(name=col_split[1], gas_concentration_in=np.nan_to_num(data['x '+col_split[1]+' (%)']), gas_concentration_out=np.nan_to_num(data[col]), conversion=np.nan_to_num((1-(data[col]/data['x '+col_split[1]+' (%)']))*100))
                    conversions.append(conversion)
                else:
                    product = Product(name=col_split[1], gas_concentration_out=np.nan_to_num(data[col]))
                    products.append(product)
                    product_names.append(col_split[1])

            if col_split[0] == "S_p":  # selectivity
                product = Product(name=col_split[1], selectivity=np.nan_to_num(data[col]))
                for i, p in enumerate(products):
                    if p.name == col_split[1]:
                        product = products.pop(i)
                        product.selectivity = np.nan_to_num(data[col])
                        break
                products.append(product)
                product_names.append(col_split[1])

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
        self.reaction_results = cat_data
        if self.reactor_filling is None and reactor_filling is not None:
            self.reactor_filling = reactor_filling

        self.reaction_results.normalize(archive, logger) #checks names of products with pubchem query

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
            archive.results.properties.catalytic.reaction.temperature = cat_data.temperature
        if cat_data.temperature is None and feed.set_temperature is not None:
            archive.results.properties.catalytic.reaction.temperature = feed.set_temperature
        if cat_data.pressure is not None:
            archive.results.properties.catalytic.reaction.pressure = cat_data.pressure
        elif feed.set_pressure is not None:
            archive.results.properties.catalytic.reaction.pressure = feed.set_pressure
        if feed.weight_hourly_space_velocity is not None:
            archive.results.properties.catalytic.reaction.weight_hourly_space_velocity = feed.weight_hourly_space_velocity
        if feed.gas_hourly_space_velocity is not None:
            archive.results.properties.catalytic.reaction.gas_hourly_space_velocity = feed.gas_hourly_space_velocity
        if products is not None:
            archive.results.properties.catalytic.reaction.products = product_results
        if self.reaction_name is not None:
            archive.results.properties.catalytic.reaction.name = self.reaction_name
            archive.results.properties.catalytic.reaction.type = self.reaction_class

        if self.samples is not None and self.samples != []:
            if self.samples[0].lab_id is not None and self.samples[0].reference is None:
                sample = CompositeSystemReference(lab_id=self.samples[0].lab_id, name=self.samples[0].name)
                sample.normalize(archive, logger)
                self.samples = []
                self.samples.append(sample)
            populate_catalyst_sampleinfo(archive, self, logger)

        ###Figures definitions###
        self.figures = []
        if self.reaction_results.time_on_stream is not None:
            x=self.reaction_results.time_on_stream.to('hour')
            x_text="time (h)"
        elif self.reaction_results.runs is not None:
            x=self.reaction_results.runs
            x_text="steps"
        else:
            number_of_runs = len(self.reaction_conditions.set_temperature)
            x = np.linspace(0, number_of_runs - 1, number_of_runs)
            x_text = "steps"

        if self.reaction_results.temperature is not None:
            fig = px.line(x=x, y=self.reaction_results.temperature.to("celsius"))
            fig.update_xaxes(title_text=x_text)
            fig.update_yaxes(title_text="Temperature (°C)")
            self.figures.append(PlotlyFigure(label='figure Temperature', figure=fig.to_plotly_json()))
            self.reaction_results.figures.append(PlotlyFigure(label='Temperature', figure=fig.to_plotly_json()))

        if cat_data.pressure is not None or feed.set_pressure is not None:
            figP = go.Figure()
            if cat_data.pressure is not None:
                figP = px.line(x=x, y=cat_data.pressure.to("bar"))
            elif feed.set_pressure is not None:
                figP = px.line(x=x, y=feed.set_pressure.to("bar"))
            figP.update_xaxes(title_text=x_text)
            figP.update_yaxes(title_text="Pressure (bar)")
            self.figures.append(PlotlyFigure(label='figure Pressure', figure=figP.to_plotly_json()))

        if self.reaction_results is not None:
            if self.reaction_results.products is not None:
                if self.reaction_results.products[0].selectivity is not None:
                    fig0 = go.Figure()
                    for i,c in enumerate(self.reaction_results.products):
                        fig0.add_trace(go.Scatter(x=x, y=self.reaction_results.products[i].selectivity, name=self.reaction_results.products[i].name))
                    fig0.update_layout(title_text="Selectivity", showlegend=True)
                    fig0.update_xaxes(title_text=x_text)
                    fig0.update_yaxes(title_text="Selectivity (%)")
                    self.figures.append(PlotlyFigure(label='figure Selectivity', figure=fig0.to_plotly_json()))
                elif self.reaction_results.products[0].gas_concentration_out is not None:
                    fig0 = go.Figure()
                    for i,c in enumerate(self.reaction_results.products):
                        fig0.add_trace(go.Scatter(x=x, y=self.reaction_results.products[i].gas_concentration_out, name=self.reaction_results.products[i].name))
                    fig0.update_layout(title_text="Gas concentration out", showlegend=True)
                    fig0.update_xaxes(title_text=x_text)
                    fig0.update_yaxes(title_text="Gas concentration out (%)")
                    self.figures.append(PlotlyFigure(label='figure Gas concentration out', figure=fig0.to_plotly_json()))

        fig1 = go.Figure()
        for i,c in enumerate(self.reaction_results.reactants_conversions):
            fig1.add_trace(go.Scatter(x=x, y=self.reaction_results.reactants_conversions[i].conversion, name=self.reaction_results.reactants_conversions[i].name))
        fig1.update_layout(title_text="Conversion", showlegend=True)
        fig1.update_xaxes(title_text=x_text)
        fig1.update_yaxes(title_text="Conversion (%)")
        self.figures.append(PlotlyFigure(label='figure Conversion', figure=fig1.to_plotly_json()))

        if self.reaction_results.rates is not None:
            fig = go.Figure()
            for i,c in enumerate(self.reaction_results.rates):
                fig.add_trace(go.Scatter(x=x, y=self.reaction_results.rates[i].reaction_rate, name=self.reaction_results.rates[i].name))
            fig.update_layout(title_text="Rates", showlegend=True)
            fig.update_xaxes(title_text=x_text)
            fig.update_yaxes(title_text="reaction rates")
            self.reaction_results.figures.append(PlotlyFigure(label='Rates', figure=fig.to_plotly_json()))
            # try:
            #     fig2 = px.line(x=self.reaction_results.temperature.to('celsius'), y=[self.reaction_results.rates[0].reaction_rate])
            #     fig2.update_xaxes(title_text="Temperature (°C)")
            #     fig2.update_yaxes(title_text="reaction rate (mmol(H2)/gcat/min)")
            #     self.figures.append(PlotlyFigure(label='figure rates', figure=fig2.to_plotly_json()))
            # except:
            #     print("No rates defined")

        if self.reaction_results.reactants_conversions is not None and self.reaction_results.products is not None:
            if self.reaction_results.products[0].selectivity is not None:
                for i,c in enumerate(self.reaction_results.reactants_conversions):
                    name=self.reaction_results.reactants_conversions[i].name
                    fig = go.Figure()
                    for j,c in enumerate(self.reaction_results.products):
                        fig.add_trace(go.Scatter(x=self.reaction_results.reactants_conversions[i].conversion, y=self.reaction_results.products[j].selectivity, name=self.reaction_results.products[j].name, mode='markers'))
                    fig.update_layout(title_text="S-X plot "+ str(i), showlegend=True)
                    fig.update_xaxes(title_text='Conversion '+ name )
                    fig.update_yaxes(title_text='Selectivity')
                    self.figures.append(PlotlyFigure(label='S-X plot '+ name+" Conversion", figure=fig.to_plotly_json()))

        return

m_package.__init_metainfo__()
