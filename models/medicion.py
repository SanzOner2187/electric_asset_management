from odoo import models, fields, api, _
from datetime import datetime, timedelta

class Medicion(models.Model):
    _name = 'electric.asset.management.medicion'
    _description = 'Mediciones de los dispositivos'

    id_dispositivo = fields.Many2one('electric.asset.management.dispositivo', string='Dispositivo')
    fecha_hora = fields.Datetime(string='Fecha y Hora')
    consumo = fields.Float(string='Consumo')
    estado_dispositivo = fields.Selection([
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
        ('En Mantenimiento', 'En Mantenimiento'),
        ('Fuera de Servicio', 'Fuera de Servicio')
    ], string="Estado del dispositivo")
    observaciones = fields.Text(string='Observaciones')
    
    # Campos para ISO 50001
    temperatura_ambiente = fields.Float(string='Temperatura Ambiente (°C)')
    humedad_relativa = fields.Float(string='Humedad Relativa (%)')
    factor_potencia = fields.Float(string='Factor de Potencia')
    desviacion_estandar = fields.Float(string='Desviación Estándar', compute='_compute_desviacion_estandar')
    es_medicion_atipica = fields.Boolean(string='Medición Atípica', compute='_compute_medicion_atipica')
    
    @api.depends('consumo')
    def _compute_desviacion_estandar(self):
        for medicion in self:
            if medicion.id_dispositivo:
                mediciones = self.search([
                    ('id_dispositivo', '=', medicion.id_dispositivo.id),
                    ('fecha_hora', '>=', fields.Datetime.to_string(datetime.now() - timedelta(days=30)))
                ], limit=100)
                consumos = mediciones.mapped('consumo')
                if len(consumos) > 1:
                    mean = sum(consumos) / len(consumos)
                    variance = sum((x - mean) ** 2 for x in consumos) / len(consumos)
                    medicion.desviacion_estandar = variance ** 0.5
                else:
                    medicion.desviacion_estandar = 0.0
            else:
                medicion.desviacion_estandar = 0.0
    
    @api.depends('consumo', 'desviacion_estandar')
    def _compute_medicion_atipica(self):
        for medicion in self:
            if medicion.id_dispositivo and medicion.desviacion_estandar > 0:
                mediciones = self.search([
                    ('id_dispositivo', '=', medicion.id_dispositivo.id),
                    ('fecha_hora', '>=', fields.Datetime.to_string(datetime.now() - timedelta(days=30)))
                ], limit=100)
                if mediciones:
                    consumos = mediciones.mapped('consumo')
                    mean = sum(consumos) / len(consumos)
                    medicion.es_medicion_atipica = abs(medicion.consumo - mean) > 2 * medicion.desviacion_estandar
                else:
                    medicion.es_medicion_atipica = False
            else:
                medicion.es_medicion_atipica = False
     
    @api.model
    def create(self, vals):
        medicion = super(Medicion, self).create(vals)
        if medicion.es_medicion_atipica and medicion.id_dispositivo:
            alerta_vals = {
                'id_dispositivo': medicion.id_dispositivo.id,
                'tipo_alerta': 'advertencia',
                'descripcion': _("Medición atípica registrada para %s: %.2f W") % (medicion.id_dispositivo.name, medicion.consumo),
                'prioridad': 'media',
                'responsable': medicion.id_dispositivo.id_usuario.id
            }
            self.env['electric.asset.management.alerta'].create(alerta_vals)
        return medicion