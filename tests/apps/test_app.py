def test_importing_app():
    # this will raise an exception if pydantic model validation fails for th app
    from nomad_catalysis_test.apps import myapp

    assert myapp.app.label == 'MyApp'

