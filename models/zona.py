from odoo import models, fields, api, _
from datetime import datetime

class Zona(models.Model):
    _name = 'electric.asset.management.zona'
    _description = 'Zonas de la empresa'

    name = fields.Char(string='Nombre', required=True)
    description = fields.Text(string='Descripción')
    ubicacion = fields.Char(string='Ubicación')
    fecha_registro = fields.Datetime(string='Fecha de Registro', default=fields.Datetime.now)
    objetivo_reduccion = fields.Float(string='Objetivo de Reducción (%)', help="Objetivo de reducción de consumo energético según ISO 50001")
    consumo_referencia = fields.Float(string='Consumo de Referencia (kWh)', help="Consumo base para comparar mejoras")
    area_m2 = fields.Float(string='Área (m²)', help="Área de la zona para calcular intensidad energética")
    intensidad_energetica = fields.Float(string='Intensidad Energética (kWh/m²)', compute='_compute_intensidad_energetica', store=True)
    
    es_area_critica = fields.Boolean(string='Área Crítica', help="Áreas con mayor consumo energético según análisis ISO 50001")
    responsable_energia = fields.Many2one('electric.asset.management.usuario', string='Responsable Energía')
    ultima_auditoria = fields.Date(string='Última Auditoría Energética')
    proxima_auditoria = fields.Date(string='Próxima Auditoría Energética')
    observaciones_energia = fields.Text(string='Observaciones Energéticas')
    
    @api.depends('consumo_referencia', 'area_m2')
    def _compute_intensidad_energetica(self):
        for zona in self:
            zona.intensidad_energetica = zona.consumo_referencia / zona.area_m2 if zona.area_m2 > 0 else 0.0