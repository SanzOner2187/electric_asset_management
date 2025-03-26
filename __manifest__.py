# -*- coding: utf-8 -*-
{
    'name': "Gestión Energética ISO 50001",
    'summary': "Sistema de gestión energética para cumplir con ISO 50001",
    'description': "Incluye políticas energéticas, metas, auditorías, alertas automáticas y reportes.",
    'author': "Sanz y compañia",
    'website': "portafolio de creaciones",
    'category': 'Accounting',
    'version': '0.1',
    'depends': ['base', 'mail'], 
    'data': [
        'views/electric_dashboard.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'static/src/js/electric_dashboard.js',
        ],
    },
    'controllers': [
        'controllers/dashboard.py',
    ],
    'installable': True,
    'application': True,
}
