from nomad.config.models.plugins import SchemaPackageEntryPoint
from pydantic import Field


class MySchemaPackageEntryPoint(SchemaPackageEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):
        from nomad_catalysis_test.schema_packages.mypackage import m_package

        return m_package

class CatalystMeasurementPackageEntryPoint(SchemaPackageEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):
        from nomad_catalysis_test.schema_packages.catalyst_measurement import m_package

        return m_package

mypackage = MySchemaPackageEntryPoint(
    name='MyPackage',
    description='Schema package defined using the new plugin mechanism.',
)

catalystmeasurement = CatalystMeasurementPackageEntryPoint(
    name='CatalystMeasurement',
    description='Catalyst Measurement Schema package defined using the new plugin mechanism.',
)