import os
from typing import (
    TYPE_CHECKING,
)

import numpy as np
import plotly.express as px
from nomad.config import config
from nomad.datamodel.data import ArchiveSection, Schema
from nomad.datamodel.metainfo.annotations import ELNAnnotation, ELNComponentEnum
from nomad.datamodel.metainfo.basesections import (
    CompositeSystemReference,
    InstrumentReference,
    Measurement,
)
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import Quantity, SchemaPackage, Section

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )
    from structlog.stdlib import (
        BoundLogger,
    )

configuration = config.get_plugin_entry_point(
    'nomad_catalysis_test.schema_packages:mypackage'
)

m_package = SchemaPackage()


class MySchema(Schema):
    name = Quantity(
        type=str, a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity)
    )
    message = Quantity(type=str)

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        logger.info('MySchema.normalize', parameter=configuration.parameter)
        self.message = f'Hello {self.name}!'


class NRVSResult(ArchiveSection):
    m_def = Section()

    array_index = Quantity(
        type=np.float64,
        shape=['*'],
        description=(
            'A placeholder for the indices of vectorial quantities. '
            'Used as x-axis for plots within quantities.'
        ),
        a_display={'visible': False},
    )
    intensity = Quantity(
        type=np.float64,
        shape=['*'],
        unit='dimensionless',
        description='The 57Fe PVDOS count at each wavenumber value, dimensionless',
        a_plot={'x': 'array_index', 'y': 'intensity'},
    )
    wavenumber = Quantity(
        type=np.float64,
        shape=['*'],
        unit='1/cm',
        description='The wavenumber range of the spectrum',
        a_eln=ELNAnnotation(defaultDisplayUnit='1/cm'),
        a_plot={'x': 'array_index', 'y': 'wavenumber'},
    )


class NRVSpectroscopy(Measurement, PlotSection, Schema):
    m_def = Section(
        label = 'NRVS measurement entry'
    )
    data_file = Quantity(
        type=str,
        description="""
            experimental tab data file
            """,
        a_eln=ELNAnnotation(component='FileEditQuantity'),
        a_browser=dict(adaptor='RawFileAdaptor'),
    )

    method = Quantity(
        type=str,
        description="""
            name of the method
            """,
        default='Nuclear resonance vibrational spectroscopy (NRVS)',
        a_eln=ELNAnnotation(
            component='StringEditQuantity',
            props=dict(
                suggestions=[
                    'experimental nuclear resonance vibrational spectroscopy',
                    'simulated nuclear resonance vibrational spectroscopy',
                ]
            ),
        ),
    )

    results = Measurement.results.m_copy()
    results.section_def = NRVSResult

    def normalize(self, archive, logger):
        super().normalize(archive, logger)
        if self.data_file is None:
            return

        if (self.data_file is not None) and (
            os.path.splitext(self.data_file)[-1] != '.dat'):
            raise ValueError('Unsupported file format. Only .dat file')

        if self.data_file.endswith('.dat'):
            with archive.m_context.raw_file(self.data_file) as f:
                import pandas as pd

                col_names = ['wavenumber, cm-1', '57Fe PVDOS']
                data = pd.read_csv(f.name, header=None, names=col_names)

            result = NRVSResult()
            result.wavenumber = data['wavenumber, cm-1']
            result.intensity = data['57Fe PVDOS']
            results = []
            results.append(result)
            self.results = results

            if self.data_file.endswith('_NRVS_exp.dat'):
                sample_name = str(self.data_file).split('_NRVS')
                if self.samples is None or self.samples == []:
                    sample = CompositeSystemReference()
                    sample.name = sample_name[0]
                    sample.lab_id = sample_name[0]
                    from nomad.datamodel.context import ClientContext
                    if isinstance(archive.m_context, ClientContext):
                        pass
                    else:
                        sample.normalize(archive, logger)
                    samples = []
                    samples.append(sample)
                    self.samples = samples

                self.method = 'experimental nuclear resonance vibrational spectroscopy'
                if self.instruments is None or self.instruments == []:
                    instrument = InstrumentReference()
                    instrument.name = 'NRVS setup'
                    instrument.lab_id = 'NRVS-setup'
                    from nomad.datamodel.context import ClientContext
                    if isinstance(archive.m_context, ClientContext):
                        pass
                    else:
                        instrument.normalize(archive, logger)
                    instruments = []
                    instruments.append(instrument)
                    self.instruments = instruments
            elif self.data_file.endswith('_NRVS_sim.dat'):
                self.method = 'simulated nuclear resonance vibrational spectroscopy'

        self.figures = []
        fig = px.line(x=data['wavenumber, cm-1'], y=data['57Fe PVDOS'])
        fig.update_xaxes(title_text=col_names[0])
        fig.update_yaxes(title_text=col_names[1])
        self.figures.append(PlotlyFigure(label='NRVS', figure=fig.to_plotly_json()))

        super().normalize(archive, logger)

m_package.__init_metainfo__()
