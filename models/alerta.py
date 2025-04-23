from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class Alerta(models.Model):
    _name = 'electric.asset.management.alerta'
    _description = 'Modelo para gestionar alertas de dispositivos eléctricos'

    # Campos principales
    id_dispositivo = fields.Many2one('electric.asset.management.dispositivo', string='Dispositivo', required=True)
    tipo_alerta = fields.Selection([
        ('advertencia', 'Advertencia'),
        ('manual', 'Manual')
    ], string='Tipo de Alerta', required=True)
    descripcion = fields.Text(string='Descripción', required=True)
    fecha_hora = fields.Datetime(string='Fecha y Hora', default=fields.Datetime.now, readonly=True)
    estado = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('resuelta', 'Resuelta')
    ], string='Estado de la Alerta', default='pendiente', required=True)
    prioridad = fields.Selection([
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta')
    ], string='Prioridad', default='media', required=True)
    acciones_tomadas = fields.Text(string='Acciones Tomadas')
    responsable = fields.Many2one('electric.asset.management.usuario', string='Responsable', required=True)
    fecha_resolucion = fields.Datetime(string='Fecha de Resolución', readonly=True)
    contacto_responsable = fields.Many2one('res.users', string='Contacto Responsable')

    # Categoría e impacto energético
    categoria = fields.Selection([
        ('consumo', 'Exceso de Consumo'),
        ('eficiencia', 'Baja Eficiencia'),
        ('mantenimiento', 'Mantenimiento Requerido'),
        ('calibracion', 'Necesita Calibración'),
        ('seguridad', 'Problema de Seguridad')
    ], string='Categoría', required=True)
    impacto_energetico = fields.Selection([
        ('alto', 'Alto'),
        ('medio', 'Medio'),
        ('bajo', 'Bajo')
    ], string='Impacto Energético', required=True)

    # Recomendaciones calculadas
    recomendaciones = fields.Text(string='Recomendaciones', compute='_compute_recomendaciones')

    # Referencia a medición
    medicion_id = fields.Many2one(
        'electric.asset.management.medicion', 
        string='Medición', 
        help='Referencia a la medición asociada a esta alerta.'
    )

    # Validaciones
    @api.constrains('fecha_hora', 'fecha_resolucion')
    def _check_fechas(self):
        for alerta in self:
            if alerta.fecha_resolucion and alerta.fecha_resolucion < alerta.fecha_hora:
                raise ValidationError(_("La fecha de resolución no puede ser anterior a la fecha de creación."))

    @api.depends('categoria', 'id_dispositivo')
    def _compute_recomendaciones(self):
        """Genera recomendaciones basadas en la categoría y el dispositivo."""
        for alerta in self:
            recomendaciones = []
            if alerta.categoria == 'consumo':
                recomendaciones.extend([
                    _("Verificar configuración del equipo."),
                    _("Evaluar horario de uso para reducir consumo.")
                ])
                if alerta.id_dispositivo and alerta.id_dispositivo.modo_bajo_consumo:
                    recomendaciones.append(_("Asegurar que el modo bajo consumo esté activado."))
            elif alerta.categoria == 'eficiencia':
                recomendaciones.extend([
                    _("Realizar mantenimiento preventivo."),
                    _("Verificar calibración del equipo."),
                    _("Considerar reemplazo por modelo más eficiente.")
                ])
            elif alerta.categoria == 'mantenimiento':
                recomendaciones.extend([
                    _("Programar mantenimiento según manual del fabricante."),
                    _("Verificar filtros y componentes críticos.")
                ])
            alerta.recomendaciones = "\n".join(recomendaciones) if recomendaciones else _("No hay recomendaciones específicas.")

    # Acción para resolver una alerta
    def action_resolver_alerta(self):
        """Marca la alerta como resuelta y registra la fecha de resolución."""
        self.ensure_one()
        if not self.acciones_tomadas:
            raise ValidationError(_("Debe especificar las acciones tomadas antes de resolver la alerta."))
        self.write({
            'estado': 'resuelta',
            'fecha_resolucion': fields.Datetime.now()
        })
        if self.id_dispositivo:
            self.id_dispositivo.message_post(
                body=_("Alerta resuelta: %s\nAcciones tomadas: %s") % (self.descripcion, self.acciones_tomadas)
            )

    # Generar reporte
    def action_generar_reporte(self):
        """Genera un reporte basado en la alerta."""
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
    
    # metodo para extraer datos para el dashboard
    def data_alerta_dashboard(self):
        """
        Método para extraer datos clave del modelo Alerta para mostrar en un dashboard.
        """
        # obtener las alertas
        alertas = self.env['electric.asset.management.alerta'].search([])

        # datos para kpis
        total_alertas = len(alertas)
        alertas_pendientes = len(alertas.filtered(lambda a: a.estado == 'pendiente'))
        alertas_resueltas = len(alertas.filtered(lambda a: a.estado == 'resuelta'))

        # datos para gráficos
        alertas_por_prioridad = {
            dict(alertas._fields['prioridad'].selection)[p]: len(alertas.filtered(lambda a: a.prioridad == p))
            for p in ['baja', 'media', 'alta']
        }

        alertas_por_categoria = {
            dict(alertas._fields['categoria'].selection)[c]: len(alertas.filtered(lambda a: a.categoria == c))
            for c in ['consumo', 'eficiencia', 'mantenimiento', 'calibracion', 'seguridad']
        }

        # ultimas 5 alertas registradas
        ultimas_alertas = alertas.sorted(key=lambda a: a.fecha_hora, reverse=True)[:5]
        ultimas_alertas_data = [
            {
                'dispositivo': a.id_dispositivo.name or 'Sin dispositivo',
                'tipo': dict(a._fields['tipo_alerta'].selection).get(a.tipo_alerta),
                'estado': dict(a._fields['estado'].selection).get(a.estado),
                'fecha': a.fecha_hora.strftime('%Y-%m-%d %H:%M:%S'),
            }
            for a in ultimas_alertas
        ]

        # retornar datos
        return {
            'kpi': {
                'total_alertas': total_alertas,
                'alertas_pendientes': alertas_pendientes,
                'alertas_resueltas': alertas_resueltas,
            },
            'graficos': {
                'por_prioridad': alertas_por_prioridad,
                'por_categoria': alertas_por_categoria,
            },
            'ultimas_alertas': ultimas_alertas_data,
        }