# -*- coding: utf-8 -*-
{
    'name': "Gestión Energética ISO 50001",
    'summary': "Sistema de gestión energética para cumplir con ISO 50001",
    'description': "Incluye políticas energéticas, metas, auditorías, alertas automáticas y reportes.",
    'author': "Sanz y compañia",
    'website': "portafolio de creaciones",
    'category': 'Accounting',
    'version': '0.1',
    'depends': ['base', 'mail', 'web'], 
    'data': [
        'views/menu_views.xml',
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
    'installable': True,
    'application': True,
}