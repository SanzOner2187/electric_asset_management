# -*- coding: utf-8 -*-
{
    'name': "Electric Asset Management",
    'summary': "Sistema de gestión energética para cumplir con ISO 50001",
    'description': "Incluye políticas energéticas, metas, auditorías, alertas automáticas y reportes.",
    'author': "Sanz y compañia",
    'website': "portafolio de creaciones",
    'category': 'Accounting',
    'version': '1.0',
    'depends': ['base', 'web'], 
    'data': [
        'views/menu_views.xml',
        'views/dashboard_views.xml',
        'views/zona_views.xml',
        'views/dispositivo_views.xml',
        'views/medicion_views.xml',
        'views/alerta_views.xml',
        'views/usuario_views.xml',
        'views/reporte_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'assets' : {
        'web.assets_backend' : [
            'electric_asset_management/static/src/components/**/*.js',
            'electric_asset_management/static/src/components/**/*.xml',
            'electric_asset_management/static/src/Chart/chart.umd.js',
        ],
    },
    'installable': True,
    'application': True,
}