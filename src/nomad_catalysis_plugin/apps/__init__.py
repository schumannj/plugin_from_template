from nomad.config.models.plugins import AppEntryPoint
from nomad.config.models.ui import App, Column, Columns, FilterMenu, FilterMenus

myapp = AppEntryPoint(
    name='MyTestCatalysisApp',
    description='App defined using the new plugin mechanism.',
    app=App(
        label='MyTestCatalysisApp',
        path='mytestcatalysisapp',
        category='Use Cases',
        columns=Columns(
            selected=['entry_id'],
            options={
                'entry_id': Column(),
            },
        ),
        filter_menus=FilterMenus(
            options={
                'material': FilterMenu(label='Material'),
            }
        ),
        dashboard={
            'widgets': [
                {
                    'layout':{
                        'lg': {'h': 10, 'minH': 8, 'minW': 12, 'w': 16, 'x': 0, 'y': 6},
                        'md': {'h': 8, 'minH': 8, 'minW': 12, 'w': 12, 'x': 0, 'y': 5},
                        'sm': {'h': 8, 'minH': 8, 'minW': 12, 'w': 12, 'x': 0, 'y': 4},
                        'xl': {'h': 10, 'minH': 8, 'minW': 12, 'w': 16, 'x': 0, 'y': 6},
                        'xxl': {'h': 10, 'minH': 8, 'minW': 12, 'w': 16, 'x': 0, 'y': 6},
                    },
                    'quantity': 'results.material.elements',
                    'scale': 'linear',
                    'type': 'periodictable',
                },
                {
                    'layout':{
                        'lg': {'h': 6, 'minH': 3, 'minW': 3, 'w': 8, 'x': 8, 'y': 0},
                        'md': {'h': 5, 'minH': 3, 'minW': 3, 'w': 6, 'x': 6, 'y': 0},
                        'sm': {'h': 4, 'minH': 4, 'minW': 3, 'w': 4, 'x': 4, 'y': 0},
                        'xl': {'h': 6, 'minH': 3, 'minW': 3, 'w': 8, 'x': 8, 'y': 0},
                        'xxl': {'h': 6, 'minH': 3, 'minW': 3, 'w': 8, 'x': 8, 'y': 0},
                    },
                    'title': 'Reactants',
                    'quantity': 'results.properties.catalytic.reaction.reactants.name',
                    'scale': 'linear',
                    'showinput': 'true',
                    'type': 'terms',
                },
                {
                    'layout':{
                        'lg': {'h': 6, 'minH': 3, 'minW': 3, 'w': 8, 'x': 0, 'y': 0},
                        'md': {'h': 5, 'minH': 3, 'minW': 3, 'w': 6, 'x': 0, 'y': 0},
                        'sm': {'h': 4, 'minH': 3, 'minW': 3, 'w': 4, 'x': 0, 'y': 0},
                        'xl': {'h': 6, 'minH': 3, 'minW': 3, 'w': 8, 'x': 0, 'y': 0},
                        'xxl': {'h': 6, 'minH': 3, 'minW': 3, 'w': 8, 'x': 0, 'y': 0},
                    },
                    'title': 'Reaction Name',
                    'quantity': 'results.properties.catalytic.reaction.name',
                    'scale': 'linear',
                    'showinput': 'true',
                    'type': 'terms',
                },
                {
                    'layout':{
                        'lg': {'h': 6, 'minH': 3, 'minW': 3, 'w': 8, 'x': 16, 'y': 0},
                        'md': {'h': 5, 'minH': 3, 'minW': 3, 'w': 6, 'x': 12, 'y': 0},
                        'sm': {'h': 4, 'minH': 3, 'minW': 3, 'w': 4, 'x': 8, 'y': 0},
                        'xl': {'h': 6, 'minH': 3, 'minW': 3, 'w': 8, 'x': 16, 'y': 0},
                        'xxl': {'h': 6, 'minH': 3, 'minW': 3, 'w': 8, 'x': 16, 'y': 0}},
                    'title': 'Products',
                    'quantity': 'results.properties.catalytic.reaction.products.name',
                    'scale': 'linear',
                    'showinput': 'true',
                    'type': 'terms'
                }
        #   - layout:
        #       lg: {h: 5, minH: 3, minW: 3, w: 8, x: 16, y: 6}
        #       md: {h: 4, minH: 3, minW: 3, w: 6, x: 12, y: 5}
        #       sm: {h: 3, minH: 3, minW: 3, w: 6, x: 0, y: 12}
        #       xl: {h: 5, minH: 3, minW: 3, w: 8, x: 16, y: 6}
        #       xxl: {h: 5, minH: 3, minW: 3, w: 8, x: 16, y: 6}
        #     quantity: results.properties.catalytic.catalyst_synthesis.preparation_method
        #     scale: linear
        #     showinput: true
        #     type: terms
        #   - layout:
        #       lg: {h: 5, minH: 3, minW: 3, w: 8, x: 16, y: 11}
        #       md: {h: 4, minH: 3, minW: 3, w: 6, x: 12, y: 9}
        #       sm: {h: 3, minH: 3, minW: 3, w: 6, x: 6, y: 12}
        #       xl: {h: 5, minH: 3, minW: 3, w: 8, x: 16, y: 11}
        #       xxl: {h: 5, minH: 3, minW: 3, w: 8, x: 16, y: 11}
        #     quantity: results.properties.catalytic.catalyst_synthesis.catalyst_type
        #     scale: linear
        #     showinput: true
        #     type: terms
        #   - autorange: false
        #     layout:
        #       lg: {h: 5, minH: 3, minW: 8, w: 12, x: 12, y: 21}
        #       md: {h: 3, minH: 3, minW: 8, w: 9, x: 9, y: 16}
        #       sm: {h: 3, minH: 3, minW: 6, w: 6, x: 6, y: 18}
        #       xl: {h: 4, minH: 3, minW: 8, w: 12, x: 12, y: 20}
        #       xxl: {h: 4, minH: 3, minW: 8, w: 12, x: 12, y: 20}
        #     nbins: 30
        #     x:
        #       quantity: results.properties.catalytic.reaction.weight_hourly_space_velocity
        #       unit: 'ml/(g*s)'
        #     title: 'Reaction Weight Hourly Space Velocity'
        #     scale: linear
        #     showinput: false
        #     type: histogram
        #   - autorange: true
        #     layout:
        #       lg: {h: 10, minH: 3, minW: 8, w: 12, x: 0, y: 16}
        #       md: {h: 6, minH: 3, minW: 8, w: 9, x: 0, y: 13}
        #       sm: {h: 6, minH: 3, minW: 6, w: 6, x: 0, y: 15}
        #       xl: {h: 8, minH: 3, minW: 8, w: 12, x: 0, y: 16}
        #       xxl: {h: 8, minH: 6, minW: 8, w: 12, x: 0, y: 16}
        #     markers:
        #       color:
        #         quantity: results.properties.catalytic.reaction.reactants[*].name
        #     size: 1000
        #     x:
        #       quantity: results.properties.catalytic.reaction.reactants[*].gas_concentration_in
        #       title: 'gas concentration (%)'
        #     y:
        #       quantity: results.properties.catalytic.reaction.temperature
        #     title: 'Reactant feed concentration vs. Temperature'
        #     type: scatterplot
        #   - autorange: false
        #     layout:
        #       lg: {h: 5, minH: 3, minW: 8, w: 12, x: 12, y: 16}
        #       md: {h: 3, minH: 3, minW: 8, w: 9, x: 9, y: 13}
        #       sm: {h: 3, minH: 3, minW: 6, w: 6, x: 6, y: 15}
        #       xl: {h: 4, minH: 3, minW: 8, w: 12, x: 12, y: 16}
        #       xxl: {h: 4, minH: 3, minW: 8, w: 12, x: 12, y: 16}
        #     nbins: 30
        #     x:
        #       quantity: results.properties.catalytic.reaction.pressure
        #       unit: 'bar'
        #     title: 'Reaction Pressure'
        #     scale: linear
        #     showinput: false
        #     type: histogram
        #   - autorange: true
        #     layout:
        #       lg: {h: 8, minH: 3, minW: 3, w: 12, x: 0, y: 26}
        #       md: {h: 6, minH: 3, minW: 3, w: 9, x: 0, y: 19}
        #       sm: {h: 5, minH: 3, minW: 3, w: 6, x: 0, y: 21}
        #       xl: {h: 9, minH: 3, minW: 3, w: 12, x: 0, y: 24}
        #       xxl: {h: 9, minH: 3, minW: 3, w: 12, x: 0, y: 24}
        #     markers:
        #       color:
        #         quantity: results.properties.catalytic.reaction.reactants[*].name
        #     size: 1000
        #     title: 'Temperature vs. Conversion'
        #     type: scatterplot
        #     x:
        #       quantity: results.properties.catalytic.reaction.temperature
        #     y:
        #       quantity: results.properties.catalytic.reaction.reactants[*].conversion
        #       title: 'Conversion (%)'
        #   - autorange: true
        #     layout:
        #       lg: {h: 8, minH: 3, minW: 3, w: 12, x: 12, y: 26}
        #       md: {h: 6, minH: 3, minW: 3, w: 9, x: 9, y: 19}
        #       sm: {h: 5, minH: 3, minW: 3, w: 6, x: 6, y: 21}
        #       xl: {h: 9, minH: 3, minW: 3, w: 12, x: 12, y: 24}
        #       xxl: {h: 9, minH: 3, minW: 3, w: 12, x: 12, y: 24}
        #     markers:
        #       color:
        #         quantity: results.properties.catalytic.reaction.products[*].name
        #     size: 1000
        #     title: 'Temperature vs. Selectivity'
        #     type: scatterplot
        #     x:
        #       quantity: results.properties.catalytic.reaction.temperature
        #     y:
        #       quantity: results.properties.catalytic.reaction.products[*].selectivity
        #       title: 'Selectivity (%)'
        #   - autorange: true
        #     layout:
        #       lg: {h: 8, minH: 3, minW: 3, w: 12, x: 0, y: 34}
        #       md: {h: 6, minH: 3, minW: 3, w: 9, x: 0, y: 25}
        #       sm: {h: 5, minH: 3, minW: 3, w: 6, x: 0, y: 26}
        #       xl: {h: 9, minH: 3, minW: 3, w: 12, x: 0, y: 33}
        #       xxl: {h: 9, minH: 3, minW: 3, w: 12, x: 0, y: 33}
        #     markers:
        #       color:
        #         quantity: results.properties.catalytic.reaction.name
        #     size: 1000
        #     type: scatterplot
        #     x:
        #       quantity: results.properties.catalytic.reaction.reactants[? name=='molecular oxygen'].conversion
        #       title: 'Oxygen Conversion (%)'
        #     y:
        #       quantity: results.properties.catalytic.reaction.products[? name=='acetic acid'].selectivity
        #       title: 'Acetic Acid Selectivity (%)'
        #   - autorange: true
        #     layout:
        #       lg: {h: 8, minH: 3, minW: 3, w: 12, x: 12, y: 34}
        #       md: {h: 6, minH: 3, minW: 3, w: 9, x: 9, y: 25}
        #       sm: {h: 5, minH: 3, minW: 3, w: 6, x: 6, y: 26}
        #       xl: {h: 9, minH: 3, minW: 3, w: 12, x: 12, y: 33}
        #       xxl: {h: 9, minH: 3, minW: 3, w: 12, x: 12, y: 33}
        #     markers:
        #       color:
        #         quantity: results.properties.catalytic.catalyst_synthesis.preparation_method
        #     size: 1000
        #     type: scatterplot
        #     x:
        #       quantity: results.properties.catalytic.reaction.reactants[? name=='carbon monoxide'].conversion
        #       title: 'Carbon Monoxide Conversion (%)'
        #     y:
        #       quantity: results.properties.catalytic.reaction.products[? name=='ethanol'].selectivity
        #       title: 'Ethanol Selectivity (%)'
        #   - autorange: false
        #     layout:
        #       lg: {h: 4, minH: 3, minW: 8, w: 12, x: 0, y: 42}
        #       md: {h: 4, minH: 3, minW: 8, w: 9, x: 0, y: 31}
        #       sm: {h: 4, minH: 3, minW: 8, w: 8, x: 0, y: 31}
        #       xl: {h: 4, minH: 3, minW: 8, w: 12, x: 0, y: 42}
        #       xxl: {h: 4, minH: 3, minW: 8, w: 12, x: 0, y: 42}
        #     nbins: 30
        #     x:
        #       quantity: results.properties.catalytic.catalyst_characterization.surface_area
        #       unit: 'm^2/g'
        #     title: 'Catalyst Surface Area'
        #     scale: 1/4
        #     showinput: false
        #     type: histogram
        #   - layout:
        #       lg: {h: 4, minH: 3, minW: 3, w: 12, x: 12, y: 42}
        #       md: {h: 4, minH: 3, minW: 3, w: 9, x: 9, y: 31}
        #       sm: {h: 4, minH: 4, minW: 3, w: 8, x: 8, y: 31}
        #       xl: {h: 4, minH: 3, minW: 3, w: 12, x: 12, y: 42}
        #       xxl: {h: 4, minH: 3, minW: 3, w: 12, x: 12, y: 42}
        #     quantity: results.properties.catalytic.catalyst_characterization.method
        #     scale: linear
        #     showinput: true
        #     type: terms
            ]
        }
    ),
)
