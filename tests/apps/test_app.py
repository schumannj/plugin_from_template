def test_importing_app():
    # this will raise an exception if pydantic model validation fails for th app
    from nomad_catalysis_test.apps.heterogeneous_catalysis_app import (
        heterogeneous_catalysis_app,
    )

