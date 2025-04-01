from odoo import models, fields, api, _
from datetime import datetime

class Alerta(models.Model):
    _name = 'electric.asset.management.alerta'
    _description = 'Alertas de los dispositivos'

    id_dispositivo = fields.Many2one('electric.asset.management.dispositivo', string='Dispositivo')
    tipo_alerta = fields.Selection([
        ('critica', 'Crítica'),
        ('advertencia', 'Advertencia'),
        ('informacional', 'Informacional')
    ], string='Tipo de Alerta', required=True)
    descripcion = fields.Text(string='Descripción')
    fecha_hora = fields.Datetime(string='Fecha y Hora', default=fields.Datetime.now)
    estado = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('resuelta', 'Resuelta')
    ], string='Estado de la Alerta', default='pendiente')
    prioridad = fields.Selection([
        ('alta', 'Alta'),
        ('media', 'Media'),
        ('baja', 'Baja')
    ], string='Prioridad', default='media')
    acciones_tomadas = fields.Text(string='Acciones Tomadas')
    responsable = fields.Many2one('electric.asset.management.usuario', string='Responsable')
    fecha_resolucion = fields.Datetime(string='Fecha de Resolución')
    
    categoria = fields.Selection([
        ('consumo', 'Exceso de Consumo'),
        ('eficiencia', 'Baja Eficiencia'),
        ('mantenimiento', 'Mantenimiento Requerido'),
        ('calibracion', 'Necesita Calibración'),
        ('seguridad', 'Problema de Seguridad')
    ], string='Categoría')
    impacto_energetico = fields.Selection([
        ('alto', 'Alto'),
        ('medio', 'Medio'),
        ('bajo', 'Bajo')
    ], string='Impacto Energético')
    recomendaciones = fields.Text(string='Recomendaciones', compute='_compute_recomendaciones')
    
    @api.depends('categoria', 'id_dispositivo')
    def _compute_recomendaciones(self):
        for alerta in self:
            recomendaciones = []
            if alerta.categoria == 'consumo':
                recomendaciones.append(_("Verificar configuración del equipo."))
                recomendaciones.append(_("Evaluar horario de uso para reducir consumo."))
                if alerta.id_dispositivo and alerta.id_dispositivo.modo_bajo_consumo:
                    recomendaciones.append(_("Asegurar que el modo bajo consumo esté activado."))
            elif alerta.categoria == 'eficiencia':
                recomendaciones.append(_("Realizar mantenimiento preventivo."))
                recomendaciones.append(_("Verificar calibración del equipo."))
                recomendaciones.append(_("Considerar reemplazo por modelo más eficiente."))
            elif alerta.categoria == 'mantenimiento':
                recomendaciones.append(_("Programar mantenimiento según manual del fabricante."))
                recomendaciones.append(_("Verificar filtros y componentes críticos."))
            alerta.recomendaciones = "\n".join(recomendaciones) if recomendaciones else _("No hay recomendaciones específicas.")
    
    def action_resolver_alerta(self):
        self.ensure_one()
        self.estado = 'resuelta'
        self.fecha_resolucion = fields.Datetime.now()
        if self.id_dispositivo:
            self.id_dispositivo.message_post(
                body=_("Alerta resuelta: %s\nAcciones tomadas: %s") % (self.descripcion, self.acciones_tomadas or _("No especificado"))
            )
        return True
    
    def action_generar_reporte(self):
        self.ensure_one()
        reporte_vals = {
            'tipo_reporte': 'repentino',
            'contenido': _("Reporte generado a partir de alerta:\n\nDispositivo: %s\nTipo: %s\nDescripción: %s\n\nAcciones tomadas: %s") % 
                        (self.id_dispositivo.name if self.id_dispositivo else _("N/A"),
                         self.tipo_alerta, self.descripcion, self.acciones_tomadas or _("Ninguna")),
            'dispositivos_afectados': [(4, self.id_dispositivo.id)] if self.id_dispositivo else False,
            'recomendaciones': self.recomendaciones,
            'estado': 'generado'
        }
        return {
            'name': _('Reporte de Alerta'),
            'type': 'ir.actions.act_window',
            'res_model': 'electric.asset.management.reporte',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_' + key: val for key, val in reporte_vals.items()}
        }