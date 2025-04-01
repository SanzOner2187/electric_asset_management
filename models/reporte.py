from odoo import models, fields, api, _
from odoo.exceptions import UserError

class Reporte(models.Model):
    _name = 'electric.asset.management.reporte'
    _description = 'Reportes generados por los usuarios'

    id_usuario = fields.Many2one('electric.asset.management.usuario', string='Usuario')
    tipo_reporte = fields.Selection([
        ('semanal', 'Semanal'),
        ('mensual', 'Mensual'),
        ('repentino', 'Repentino'),
        ('auditoria', 'Auditoría'),
        ('cumplimiento', 'Cumplimiento')
    ], string='Tipo de Reporte', required=True)
    fecha_generacion = fields.Datetime(string='Fecha de Generación', default=fields.Datetime.now)
    contenido = fields.Text(string='Contenido')
    periodo_inicio = fields.Datetime(string='Inicio del Período')
    periodo_fin = fields.Datetime(string='Fin del Período')
    
    dispositivos_afectados = fields.Many2many(
        comodel_name='electric.asset.management.dispositivo',
        relation='reporte_dispositivo_rel',
        column1='reporte_id',
        column2='dispositivo_id',
        string='Dispositivos Afectados'
    )
    
    consumo_total = fields.Float(string='Consumo Total (kWh)')
    costos_asociados = fields.Float(string='Costos Asociados')
    eficiencia_energetica = fields.Float(string='Eficiencia Energética (%)')
    recomendaciones = fields.Text(string='Recomendaciones')
    estado = fields.Selection([
        ('borrador', 'Borrador'),
        ('generado', 'Generado'),
        ('enviado', 'Enviado')
    ], string='Estado del Reporte', default='borrador')
    
    objetivos_cumplidos = fields.Boolean(string='Objetivos Cumplidos', compute='_compute_objetivos_cumplidos')
    desviacion_objetivo = fields.Float(string='Desviación del Objetivo (%)', compute='_compute_desviacion_objetivo')
    enpi_promedio = fields.Float(string='EnPI Promedio', compute='_compute_enpi_promedio')
    areas_mejora = fields.Text(string='Áreas de Mejora', compute='_compute_areas_mejora')
    acciones_correctivas = fields.Text(string='Acciones Correctivas Propuestas')
    seguimiento_requerido = fields.Boolean(string='Requiere Seguimiento')
    
    @api.depends('consumo_total', 'dispositivos_afectados', 'periodo_inicio', 'periodo_fin')
    def _compute_objetivos_cumplidos(self):
        for reporte in self:
            if reporte.dispositivos_afectados and reporte.periodo_inicio and reporte.periodo_fin:
                consumo_referencia = sum(
                    dispositivo.consumo_mensual_kwh * 
                    ((reporte.periodo_fin - reporte.periodo_inicio).days / 30)
                    for dispositivo in reporte.dispositivos_afectados
                )
                if consumo_referencia > 0:
                    reduccion = 100 * (1 - (reporte.consumo_total / consumo_referencia))
                    objetivo_zona = reporte.dispositivos_afectados[0].id_zona.objetivo_reduccion if reporte.dispositivos_afectados[0].id_zona else 0
                    reporte.objetivos_cumplidos = reduccion >= objetivo_zona
                else:
                    reporte.objetivos_cumplidos = False
            else:
                reporte.objetivos_cumplidos = False
    
    @api.depends('consumo_total', 'dispositivos_afectados', 'periodo_inicio', 'periodo_fin')
    def _compute_desviacion_objetivo(self):
        for reporte in self:
            if reporte.dispositivos_afectados and reporte.periodo_inicio and reporte.periodo_fin:
                consumo_referencia = sum(
                    dispositivo.consumo_mensual_kwh * 
                    ((reporte.periodo_fin - reporte.periodo_inicio).days / 30)
                    for dispositivo in reporte.dispositivos_afectados
                )
                if consumo_referencia > 0:
                    reduccion = 100 * (1 - (reporte.consumo_total / consumo_referencia))
                    objetivo_zona = reporte.dispositivos_afectados[0].id_zona.objetivo_reduccion if reporte.dispositivos_afectados[0].id_zona else 0
                    reporte.desviacion_objetivo = reduccion - objetivo_zona
                else:
                    reporte.desviacion_objetivo = 0.0
            else:
                reporte.desviacion_objetivo = 0.0
    
    @api.depends('dispositivos_afectados')
    def _compute_enpi_promedio(self):
        for reporte in self:
            if reporte.dispositivos_afectados:
                reporte.enpi_promedio = sum(dispositivo.enpi for dispositivo in reporte.dispositivos_afectados) / len(reporte.dispositivos_afectados)
            else:
                reporte.enpi_promedio = 0.0
    
    @api.depends('dispositivos_afectados', 'objetivos_cumplidos')
    def _compute_areas_mejora(self):
        for reporte in self:
            areas = set()
            if not reporte.objetivos_cumplidos:
                areas.add(_("Reducción de consumo en equipos críticos"))
            for dispositivo in reporte.dispositivos_afectados:
                if dispositivo.eficiencia_operativa < 75.0:
                    areas.add(_("Mejora de eficiencia en %s") % dispositivo.name)
                if dispositivo.etiqueta_eficiencia in ['c', 'd']:
                    areas.add(_("Actualización de equipos con etiqueta baja (%s)") % dispositivo.name)
            reporte.areas_mejora = "\n".join(areas) if areas else _("No se identificaron áreas críticas de mejora.")
    
    def action_generar_reporte_iso50001(self):
        self.ensure_one()
        if not self.dispositivos_afectados:
            raise UserError(_("Se deben seleccionar dispositivos afectados para generar el reporte ISO 50001."))
        zonas = {dispositivo.id_zona for dispositivo in self.dispositivos_afectados if dispositivo.id_zona}
        consumo_referencia = sum(
            dispositivo.consumo_mensual_kwh * 
            ((self.periodo_fin - self.periodo_inicio).days / 30)
            for dispositivo in self.dispositivos_afectados
        )
        reduccion = 100 * (1 - (self.consumo_total / consumo_referencia)) if consumo_referencia > 0 else 0
        contenido = _("REPORTE DE DESEMPEÑO ENERGÉTICO ISO 50001\n\n")
        contenido += _("Período: %s a %s\n") % (self.periodo_inicio, self.periodo_fin)
        contenido += _("Dispositivos incluidos: %d\n") % len(self.dispositivos_afectados)
        contenido += _("Zonas afectadas: %s\n") % ", ".join(zona.name for zona in zonas)
        contenido += "\n"
        contenido += _("MÉTRICAS CLAVE:\n")
        contenido += _("- Consumo total: %.2f kWh\n") % self.consumo_total
        contenido += _("- Costo total: %.2f\n") % self.costos_asociados
        contenido += _("- Eficiencia energética promedio: %.2f%%\n") % self.eficiencia_energetica
        contenido += _("- EnPI promedio: %.2f\n") % self.enpi_promedio
        contenido += _("- Reducción respecto a referencia: %.2f%%\n") % reduccion
        contenido += _("- Objetivo cumplido: %s\n") % (_("Sí") if self.objetivos_cumplidos else _("No"))
        contenido += "\n"
        contenido += _("ANÁLISIS:\n%s\n") % self.areas_mejora
        contenido += "\n"
        contenido += _("RECOMENDACIONES:\n%s\n") % self.recomendaciones
        
        self.write({
            'contenido': contenido,
            'estado': 'generado',
            'tipo_reporte': 'auditoria'
        })
        return True
    
    def action_enviar_reporte(self):
        self.ensure_one()
        if self.estado != 'generado':
            raise UserError(_("El reporte debe estar en estado 'Generado' para poder enviarse."))
        destinatarios = set()
        for dispositivo in self.dispositivos_afectados:
            if dispositivo.id_zona and dispositivo.id_zona.responsable_energia:
                destinatarios.add(dispositivo.id_zona.responsable_energia.login)
            elif dispositivo.id_usuario:
                destinatarios.add(dispositivo.id_usuario.login)
        if not destinatarios:
            raise UserError(_("No se encontraron destinatarios para el reporte."))
        self.estado = 'enviado'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reporte Enviado'),
                'message': _('El reporte ha sido enviado a: %s') % ", ".join(destinatarios),
                'type': 'success',
                'sticky': False,
            }
        }