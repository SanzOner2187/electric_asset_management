# -*- coding: utf-8 -*-
{
    'name': "Electric Asset Management",
    'summary': "Sistema de gestión energética para cumplir con ISO 50001",
    'description': "Incluye políticas energéticas, metas, auditorías, alertas automáticas y reportes.",
    'author': "Santiago Sanchez",
    'website': "portafolio de creaciones",
    'category': 'Accounting',
    'version': '1.0',
    'depends': ['base', 'mail', 'account'], 
    'data': [
        # importar vistas
        'views/dashboard_views.xml',
        'views/menu_views.xml',
        'views/dispositivo_views.xml',
        'views/zona_views.xml',
        'views/medicion_views.xml',
        'views/alerta_views.xml',
        'views/usuario_views.xml',
        'views/reporte_views.xml',
        'views/factura_energica_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'assets' : {
        'web.assets_backend' : [
            # importar elementos del backend o frontend personalizados
            'electric_asset_management/static/src/components/**/*.js',
            'electric_asset_management/static/src/components/**/*.xml',

            #importar libreria localmente
            'electric_asset_management/static/src/Chart/chart.umd.js',
        ],
    },
    'installable': True,
    'application': True,
}