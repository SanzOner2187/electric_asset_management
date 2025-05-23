from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class Reporte(models.Model):
    _name = 'electric.asset.management.reporte'
    _description = 'Reportes generados por los usuarios'

    factura_id = fields.Many2one(
        'account.move', 
        string='Factura Energética',
        help='Factura energética asociada a este reporte.'
    )

    user_id = fields.Many2one('electric.asset.management.usuario', string='Usuario', required=True)
    tipo_reporte = fields.Selection([
        ('semanal', 'Semanal'),
        ('mensual', 'Mensual'),
        ('repentino', 'Repentino'),
        ('auditoria', 'Auditoría'),
        ('cumplimiento', 'Cumplimiento')
    ], string='Tipo de Reporte', required=True)
    prioridad = fields.Selection([
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta')
    ], string='Prioridad', default='media', required=True)
    zona_id = fields.Many2one(
        related = 'dispositivos_afectados.id_zona',
        string = 'Zona',
        required = True,
        ondelete = 'restrict',
        help = "Zona asociada al reporte"
    )
    fecha_generacion = fields.Datetime(string='Fecha de Generación', default=fields.Datetime.now)
    contenido = fields.Text(string='Contenido', required=True)
    periodo_inicio = fields.Datetime(string='Inicio del Período')
    periodo_fin = fields.Datetime(string='Fin del Período')
    
    dispositivos_afectados = fields.Many2many(
        comodel_name='electric.asset.management.dispositivo',
        relation='reporte_dispositivo_rel',
        column1='reporte_id',
        column2='dispositivo_id',
        string='Dispositivos Afectados',
        required=True
    )
    
    consumo_total = fields.Float(string='Consumo Total (kWh)', required=True)
    costos_asociados = fields.Float(string='Costos Asociados', required=True)
    eficiencia_energetica = fields.Float(string='Eficiencia Energética (%)', required=True)
    recomendaciones = fields.Text(string='Recomendaciones', required=True)
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

    # Nuevos campos para cumplir con ISO 50001 y mejorar el dashboard
    politica_energetica = fields.Text(string='Política Energética', help="Describa la política energética aplicable a este reporte.")
    resumen_dashboard = fields.Text(string='Resumen para Dashboard', compute='_compute_resumen_dashboard', store=True)
    alerta_eficiencia = fields.Boolean(string='Alerta de Eficiencia', compute='_compute_alerta_eficiencia')

    # filepath: /opt/odoo16/16.0/extra-addons/santiago/electric_asset_management/models/reporte.py
    name = fields.Char(
        string='Nombre del Reporte',
        compute='_compute_name',
        store=True,
        help="Nombre generado automáticamente para identificar el reporte"
    )

    @api.depends('tipo_reporte', 'fecha_generacion')
    def _compute_name(self):
        for reporte in self:
            reporte.name = f"{dict(self._fields['tipo_reporte'].selection).get(reporte.tipo_reporte, 'Reporte')} - {reporte.fecha_generacion.strftime('%Y-%m-%d') if reporte.fecha_generacion else ''}"

    # Validación de fechas
    @api.constrains('periodo_inicio', 'periodo_fin')
    def _check_periodo_fechas(self):
        for reporte in self:
            if reporte.periodo_inicio and reporte.periodo_fin:
                if reporte.periodo_inicio >= reporte.periodo_fin:
                    raise UserError(_("La fecha de inicio debe ser anterior a la fecha de fin."))
    # Validación de dispositivos afectados
    @api.constrains('dispositivos_afectados')
    def _check_dispositivos_zona(self):
        for reporte in self:
            zonas = {dispositivo.id_zona for dispositivo in reporte.dispositivos_afectados if dispositivo.id_zona}
            if len(zonas) > 1:
                raise UserError(_("Todos los dispositivos afectados deben pertenecer a la misma zona."))

    # Cálculo centralizado del consumo de referencia
    def _calcular_consumo_referencia(self):
        self.ensure_one()
        # Convertir los valores de los campos a objetos datetime
        periodo_inicio_dt = fields.Datetime.to_datetime(self.periodo_inicio)
        periodo_fin_dt = fields.Datetime.to_datetime(self.periodo_fin)

        # Calcular la diferencia en días
        if periodo_inicio_dt and periodo_fin_dt:
            diferencia_dias = (periodo_fin_dt - periodo_inicio_dt).days
            return sum(
                dispositivo.consumo_mensual_kwh * 
                (diferencia_dias / 30)  # Suponiendo un mes promedio de 30 días
                for dispositivo in self.dispositivos_afectados
            )
        return 0.0

    # Computar si se cumplieron los objetivos
    @api.depends('consumo_total', 'dispositivos_afectados', 'periodo_inicio', 'periodo_fin')
    def _compute_objetivos_cumplidos(self):
        for reporte in self:
            consumo_referencia = reporte._calcular_consumo_referencia()
            if consumo_referencia > 0:
                reduccion = 100 * (1 - (reporte.consumo_total / consumo_referencia))
                objetivo_zona = reporte.dispositivos_afectados[0].id_zona.objetivo_reduccion if reporte.dispositivos_afectados[0].id_zona else 0
                reporte.objetivos_cumplidos = reduccion >= objetivo_zona
            else:
                reporte.objetivos_cumplidos = False

    # Computar la desviación del objetivo
    @api.depends('consumo_total', 'dispositivos_afectados', 'periodo_inicio', 'periodo_fin')
    def _compute_desviacion_objetivo(self):
        for reporte in self:
            consumo_referencia = reporte._calcular_consumo_referencia()
            if consumo_referencia > 0:
                reduccion = 100 * (1 - (reporte.consumo_total / consumo_referencia))
                objetivo_zona = reporte.dispositivos_afectados[0].id_zona.objetivo_reduccion if reporte.dispositivos_afectados[0].id_zona else 0
                reporte.desviacion_objetivo = reduccion - objetivo_zona
            else:
                reporte.desviacion_objetivo = 0.0

    # Computar el EnPI promedio
    @api.depends('dispositivos_afectados')
    def _compute_enpi_promedio(self):
        for reporte in self:
            if reporte.dispositivos_afectados:
                reporte.enpi_promedio = sum(dispositivo.enpi for dispositivo in reporte.dispositivos_afectados) / len(reporte.dispositivos_afectados)
            else:
                reporte.enpi_promedio = 0.0

    # Computar áreas de mejora
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

    # Computar resumen para el dashboard
    @api.depends('consumo_total', 'eficiencia_energetica', 'objetivos_cumplidos')
    def _compute_resumen_dashboard(self):
        for reporte in self:
            resumen = f"Consumo: {reporte.consumo_total} kWh | Eficiencia: {reporte.eficiencia_energetica}%"
            if not reporte.objetivos_cumplidos:
                resumen += " ⚠️ Objetivo no cumplido"
            reporte.resumen_dashboard = resumen

    # Computar alerta de eficiencia
    @api.depends('eficiencia_energetica')
    def _compute_alerta_eficiencia(self):
        for reporte in self:
            reporte.alerta_eficiencia = reporte.eficiencia_energetica < 75.0

    # Acción para generar un reporte ISO 50001
    def action_generar_reporte_iso50001(self):
        self.ensure_one()
        if not self.dispositivos_afectados:
            raise UserError(_("Se deben seleccionar dispositivos afectados para generar el reporte ISO 50001."))
        zonas = {dispositivo.id_zona for dispositivo in self.dispositivos_afectados if dispositivo.id_zona}
        consumo_referencia = self._calcular_consumo_referencia()
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

    # Acción para enviar el reporte
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

    # metodo para extraer datos para el dashboard
    def data_reporte_dashboard(self):
        """
        Método para extraer datos clave del modelo Reporte para mostrar en un dashboard.
        """
        # traer reportes
        reportes = self.env['electric.asset.management.reporte'].search([])

        # datos para kpis
        total_reportes = len(reportes)
        reportes_objetivos_cumplidos = len(reportes.filtered(lambda r: r.objetivos_cumplidos))
        promedio_eficiencia = sum(r.eficiencia_energetica for r in reportes) / total_reportes if total_reportes > 0 else 0.0

        # datos para graficos
        reportes_por_tipo = {
            dict(reportes._fields['tipo_reporte'].selection)[tipo]: len(reportes.filtered(lambda r: r.tipo_reporte == tipo))
            for tipo in ['semanal', 'mensual', 'repentino', 'auditoria', 'cumplimiento']
        }

        reportes_por_estado = {
            dict(reportes._fields['estado'].selection)[estado]: len(reportes.filtered(lambda r: r.estado == estado))
            for estado in ['borrador', 'generado', 'enviado']
        }

        # ultimos 5 reportes
        ultimos_reportes = reportes.sorted(key=lambda r: r.fecha_generacion, reverse=True)[:5]
        ultimos_reportes_data = [
            {
                'tipo': dict(r._fields['tipo_reporte'].selection).get(r.tipo_reporte),
                'estado': dict(r._fields['estado'].selection).get(r.estado),
                'consumo_total': r.consumo_total,
                'eficiencia': r.eficiencia_energetica,
                'fecha_generacion': r.fecha_generacion.strftime('%Y-%m-%d %H:%M:%S'),
            }
            for r in ultimos_reportes
        ]

        # retornar datos
        return {
            'kpi': {
                'total_reportes': total_reportes,
                'objetivos_cumplidos': reportes_objetivos_cumplidos,
                'promedio_eficiencia': round(promedio_eficiencia, 2),
            },
            'graficos': {
                'por_tipo': reportes_por_tipo,
                'por_estado': reportes_por_estado,
            },
            'ultimos_reportes': ultimos_reportes_data,
        }
    
    @api.model
    def get_dashboard_data_reporte(self):
        """
        Metodo publico para hacer llamado al front end
        este metodo actua como puente para poder acceder a los datos calculados
        """
        return self.data_reporte_dashboard()