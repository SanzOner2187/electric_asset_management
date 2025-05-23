from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

import logging

_logger = logging.getLogger(__name__)

class Dispositivo(models.Model):
    _name = 'electric.asset.management.dispositivo'
    _description = 'Dispositivos de la empresa'
    _order = 'fecha_registro desc' 
    _inherit = ['mail.thread', 'mail.activity.mixin']

    factura_id = fields.Many2one(
        'account.move',  
        string='Factura Energética',
        help='Factura energética asociada a esta medición.'
    )

    name = fields.Char(string='Nombre', required=True, tracking=True)
    tipo = fields.Char(string='Tipo', tracking=True)
    marca = fields.Char(string='Marca', tracking=True)
    modelo = fields.Char(string='Modelo', tracking=True)
    consumo_energetico = fields.Float(string='Consumo Energético (Watts)', required=True, tracking=True)
    id_zona = fields.Many2one('electric.asset.management.zona', string='Zona', tracking=True)
    estado = fields.Selection([
        ('buenas_condiciones', 'Buenas Condiciones'),
        ('aceptable', 'Aceptable'),
        ('necesita_revision', 'Necesita revisión'),
        ('necesita_reparacion', 'Necesita Reparación'),
        ('mantenimiento', 'Mantenimiento'),
        ('dado_de_baja', 'Dado de baja')
    ], string="Estado del dispositivo", required=True, tracking=True)
    fecha_registro = fields.Datetime(string='Fecha de Registro', default=fields.Datetime.now, readonly=True)
    vida_util_estimada = fields.Integer(string='Vida Útil Estimada (años)', help="Vida útil estimada en años")
    cumple_estandar = fields.Boolean(string='Cumple Estándar', default=False, tracking=True)
    numero_serie = fields.Char(string='Número de Serie', tracking=True)
    horas_uso_diario = fields.Float(string='Horas de Uso Diario', default=0.0, tracking=True)
    dias_uso_semana = fields.Integer(string='Días de Uso por Semana', default=5, tracking=True)
    consumo_diario_kwh = fields.Float(string='Consumo Diario (kWh)', compute='_calcular_consumo_diario', store=True)
    consumo_mensual_kwh = fields.Float(string='Consumo Mensual (kWh)', compute='_calcular_consumo_mensual', store=True)
    costo_kwh = fields.Float(string='Costo por kWh', default=858.53, tracking=True)
    costo_diario = fields.Float(string='Costo Diario', compute='_calcular_costo_diario', store=True)
    costo_mensual = fields.Float(string='Costo Mensual', compute='_calcular_costo_mensual', store=True)
    modo_bajo_consumo = fields.Boolean(string='Modo de Bajo Consumo', default=False, tracking=True)
    potencia_bajo_consumo = fields.Float(string='Potencia en Bajo Consumo (Watts)', default=0.0, tracking=True)
    potencia_aparente_base = fields.Float(string='Potencia aparente base (kVa)', required=True, tracking=True)
    umbral_desviacion = fields.Float(string='Umbral de desviación estándar', default=2.0, help='Umbral para considerar una medición atípica (en múltiplos de la desviación estándar)')
    fecha_ultima_revision = fields.Datetime(string='Fecha de Última Revisión', tracking=True)
    id_usuario = fields.Many2one('electric.asset.management.usuario', string='Responsable', tracking=True)
    contacto_responsable = fields.Char(string='Contacto del Responsable', compute='_compute_contacto_responsable', store=True)
    antiguedad_equipo = fields.Integer(string='Antigüedad del Equipo (años)', compute='_compute_antiguedad_equipo', store=True)
    fuente_alimentacion = fields.Selection([
        ('ups', 'UPS'),
        ('regulador', 'Regulador'),
        ('directa', 'Directa a la Red')
    ], string='Fuente de Alimentación', default='directa', tracking=True)
    etiqueta_eficiencia = fields.Selection([
        ('a++', 'A++'),
        ('a+', 'A+'),
        ('a', 'A'),
        ('b', 'B'),
        ('c', 'C'),
        ('d', 'D')
    ], string='Etiqueta de Eficiencia Energética', default='b', tracking=True)

    factura_id = fields.Many2one(
        'electric.asset.management.factura.energetica',
        string='Factura Asociada',
        help="Factura energética asociada a este dispositivo"
    )

    # ISO 50001
    es_equipo_critico = fields.Boolean(string='Equipo Crítico', help="Equipos con mayor consumo según análisis ISO 50001")
    umbral_alerta_consumo = fields.Float(string='Umbral de Alerta (Watts)', help="Consumo máximo permitido antes de generar alerta")
    fecha_calibracion = fields.Date(string='Fecha de Calibración', tracking=True)
    proxima_calibracion = fields.Date(string='Próxima Calibración', compute='_compute_proxima_calibracion', store=True)
    eficiencia_operativa = fields.Float(
        string='Eficiencia Operativa (%)', 
        compute='_compute_eficiencia_operativa',
        store=True, 
        digits=(12, 2),
        help="Eficiencia operativa calculada en porcentaje"
    )
    oportunidades_mejora = fields.Text(string='Oportunidades de Mejora', compute='_compute_oportunidades_mejora')
    enpi = fields.Float(string='EnPI', compute='_compute_enpi', help="Indicador de Desempeño Energético según ISO 50001")
    medicion_ids = fields.One2many(
        'electric.asset.management.medicion', 
        'id_dispositivo', 
        string='Mediciones'
    )

    # Métodos de cálculo
    @api.depends('consumo_energetico', 'potencia_bajo_consumo', 'modo_bajo_consumo')
    def _compute_eficiencia_operativa(self):
        for dispositivo in self:
            try:
                if dispositivo.consumo_energetico > 0:
                    if dispositivo.modo_bajo_consumo and dispositivo.potencia_bajo_consumo > 0:
                        dispositivo.eficiencia_operativa = 100 * (1 - (dispositivo.potencia_bajo_consumo / dispositivo.consumo_energetico))
                    else:
                        dispositivo.eficiencia_operativa = self._get_eficiencia_estandar(dispositivo.tipo)
                else:
                    dispositivo.eficiencia_operativa = 0.0
            except Exception as e:
                _logger.error(f"Error al calcular eficiencia operativa: {e}")
                dispositivo.eficiencia_operativa = 0.0

    def _get_eficiencia_estandar(self, tipo_dispositivo):
        """Retorna valores de eficiencia estándar según tipo de dispositivo"""
        eficiencia_estandar = {
            'aire acondicionado': 85.0,
            'iluminacion': 90.0,
            'computadora': 80.0,
            'servidor': 75.0,
            'motor electrico': 88.0,
            'maquinaria': 82.0
        }
        return eficiencia_estandar.get(tipo_dispositivo.lower() if tipo_dispositivo else '', 75.0)

    @api.depends('consumo_energetico', 'eficiencia_operativa', 'etiqueta_eficiencia')
    def _compute_oportunidades_mejora(self):
        for dispositivo in self:
            recomendaciones = []
            try:
                if dispositivo.etiqueta_eficiencia in ['c', 'd']:
                    recomendaciones.append(_("Considerar reemplazo por equipo con mejor etiqueta de eficiencia (A o B)."))
                if dispositivo.eficiencia_operativa < 75.0:
                    recomendaciones.append(_("Eficiencia operativa baja. Verificar mantenimiento y calibración."))
                if dispositivo.modo_bajo_consumo and dispositivo.horas_uso_diario > 8:
                    recomendaciones.append(_("Optimizar horario de uso para aprovechar modo bajo consumo."))
                if not dispositivo.modo_bajo_consumo and dispositivo.horas_uso_diario > 4:
                    recomendaciones.append(_("Evaluar implementación de modo bajo consumo o programación de apagado automático."))
                dispositivo.oportunidades_mejora = "\n".join(recomendaciones) if recomendaciones else _("No se detectaron oportunidades de mejora significativas.")
            except Exception as e:
                _logger.error(f"Error al calcular oportunidades de mejora: {e}")
                dispositivo.oportunidades_mejora = _("Error al calcular oportunidades de mejora.")

    @api.depends('consumo_mensual_kwh', 'horas_uso_diario', 'dias_uso_semana')
    def _compute_enpi(self):
        for dispositivo in self:
            try:
                if dispositivo.horas_uso_diario > 0 and dispositivo.dias_uso_semana > 0:
                    dispositivo.enpi = dispositivo.consumo_mensual_kwh / (dispositivo.horas_uso_diario * dispositivo.dias_uso_semana * 4)
                else:
                    dispositivo.enpi = 0.0
            except ZeroDivisionError:
                _logger.warning(f"División por cero al calcular EnPI para el dispositivo {dispositivo.name}")
                dispositivo.enpi = 0.0

    # Cálculo de consumo
    @api.depends('consumo_energetico', 'horas_uso_diario')
    def _calcular_consumo_diario(self):
        for dispositivo in self:
            try:
                dispositivo.consumo_diario_kwh = (dispositivo.consumo_energetico * dispositivo.horas_uso_diario) / 1000
            except Exception as e:
                _logger.error(f"Error al calcular consumo diario: {e}")
                dispositivo.consumo_diario_kwh = 0.0

    @api.depends('consumo_diario_kwh', 'dias_uso_semana')
    def _calcular_consumo_mensual(self):
        for dispositivo in self:
            try:
                dispositivo.consumo_mensual_kwh = dispositivo.consumo_diario_kwh * dispositivo.dias_uso_semana * 4
            except Exception as e:
                _logger.error(f"Error al calcular consumo mensual: {e}")
                dispositivo.consumo_mensual_kwh = 0.0

    @api.depends('consumo_diario_kwh', 'costo_kwh')
    def _calcular_costo_diario(self):
        for dispositivo in self:
            try:
                dispositivo.costo_diario = dispositivo.consumo_diario_kwh * dispositivo.costo_kwh
            except Exception as e:
                _logger.error(f"Error al calcular costo diario: {e}")
                dispositivo.costo_diario = 0.0

    @api.depends('consumo_mensual_kwh', 'costo_kwh')
    def _calcular_costo_mensual(self):
        for dispositivo in self:
            try:
                dispositivo.costo_mensual = dispositivo.consumo_mensual_kwh * dispositivo.costo_kwh
            except Exception as e:
                _logger.error(f"Error al calcular costo mensual: {e}")
                dispositivo.costo_mensual = 0.0

    # Manejo de fechas
    @api.depends('fecha_calibracion')
    def _compute_proxima_calibracion(self):
        for dispositivo in self:
            try:
                if dispositivo.fecha_calibracion:
                    dispositivo.proxima_calibracion = dispositivo.fecha_calibracion + timedelta(days=365)
                else:
                    dispositivo.proxima_calibracion = False
            except Exception as e:
                _logger.error(f"Error al calcular próxima calibración: {e}")
                dispositivo.proxima_calibracion = False

    @api.depends('fecha_registro')
    def _compute_antiguedad_equipo(self):
        for dispositivo in self:
            try:
                if dispositivo.fecha_registro:
                    today = fields.Date.today()
                    antiguedad = (today - dispositivo.fecha_registro.date()).days // 365
                    dispositivo.antiguedad_equipo = max(0, antiguedad)
                else:
                    dispositivo.antiguedad_equipo = 0
            except Exception as e:
                _logger.error(f"Error al calcular antigüedad del equipo: {e}")
                dispositivo.antiguedad_equipo = 0

    @api.onchange('id_usuario')
    def _onchange_id_usuario(self):
        if self.id_usuario:
            self.contacto_responsable = self.id_usuario.login
        else:
            self.contacto_responsable = False

    @api.constrains('consumo_energetico', 'umbral_alerta_consumo', 'horas_uso_diario', 'dias_uso_semana')
    def _check_valores(self):
        for dispositivo in self:
            if dispositivo.umbral_alerta_consumo > 0 and dispositivo.consumo_energetico > dispositivo.umbral_alerta_consumo:
                dispositivo.action_generar_alerta_consumo()
            if dispositivo.horas_uso_diario < 0 or dispositivo.dias_uso_semana < 0:
                raise ValidationError(_("Las horas de uso diario y días de uso por semana no pueden ser negativos."))

    def action_generar_alerta_consumo(self):
        """Genera una alerta de consumo y muestra un mensaje al usuario."""
        self.ensure_one()
        try:
            if not self.umbral_alerta_consumo or self.umbral_alerta_consumo <= 0:
                raise UserError(_("El umbral de alerta de consumo no está configurado correctamente."))
            if not self.consumo_energetico or self.consumo_energetico <= 0:
                raise UserError(_("El consumo energético del dispositivo no está configurado correctamente."))

            tipo_alerta = 'critica' if self.consumo_energetico > self.umbral_alerta_consumo * 1.2 else 'advertencia'

            default_vals = {
                'id_dispositivo': self.id,
                'tipo_alerta': tipo_alerta,
                'descripcion': _("El dispositivo %s está consumiendo %s W, superando el umbral de %s W") % 
                                (self.name, self.consumo_energetico, self.umbral_alerta_consumo),
                'prioridad': 'alta',
                'responsable': self.id_usuario.id if self.id_usuario else False,
                'estado': 'pendiente', 
                'categoria': 'consumo',  
                'impacto_energetico': 'alto' if tipo_alerta == 'critica' else 'medio',  
            }
            alerta = self.env['electric.asset.management.alerta'].create(default_vals)

            return {
            'name': _('Alerta de Eficiencia Energética'),
            'type': 'ir.actions.act_window',
            'res_model': 'electric.asset.management.alerta',
            'view_mode': 'form',
            'target': 'new',  # Abre el formulario como un modal
            'context': {'default_' + key: val for key, val in default_vals.items()}  # Valores predeterminados
        }

        except UserError as ue:
            _logger.error(f"Error al generar alerta de consumo: {ue}")
            raise ue
        except Exception as e:
            _logger.error(f"Error inesperado al generar alerta de consumo: {e}")
            raise UserError(_("Ocurrió un error inesperado al generar la alerta. Por favor, revise los registros del sistema."))

    def action_generar_reporte_eficiencia(self):
        """Abre un modal para generar un reporte de eficiencia energética."""
        self.ensure_one()  # Asegurarse de que solo se ejecute para un registro

        # Preparar los valores predeterminados para el formulario
        default_vals = {
            'tipo_reporte': 'auditoria',
            'contenido': _("Reporte de Eficiencia Energética para %s\n"
                        "Eficiencia Operativa: %.2f%%\n"
                        "EnPI: %.2f\n"
                        "Oportunidades de Mejora:\n%s") %
                        (self.name, self.eficiencia_operativa, self.enpi, self.oportunidades_mejora),
            'dispositivos_afectados': [(4, self.id)],
            'consumo_total': self.consumo_mensual_kwh,
            'costos_asociados': self.costo_mensual,
            'eficiencia_energetica': self.eficiencia_operativa,
            'recomendaciones': self.oportunidades_mejora,
            'estado': 'generado'
        }

        # Abrir el formulario en modo "Crear" con valores predeterminados
        return {
            'name': _('Reporte de Eficiencia Energética'),
            'type': 'ir.actions.act_window',
            'res_model': 'electric.asset.management.reporte',
            'view_mode': 'form',
            'target': 'new',  # Abre el formulario como un modal
            'context': {'default_' + key: val for key, val in default_vals.items()}  # Valores predeterminados
        }

    from odoo import models

    def data_dispositivo_dashboard(self):
        """
        Método para extraer datos clave del modelo Dispositivo para mostrar en un dashboard.
        """
        # Consulta principal para obtener todos los dispositivos
        dispositivos = self.env['electric.asset.management.dispositivo'].search([])

        # Datos para KPIs
        total_dispositivos = self.env['electric.asset.management.dispositivo'].search_count([])
        equipos_criticos = len(dispositivos.filtered(lambda d: d.es_equipo_critico))
        consumo_total_mensual = sum(dispositivos.mapped('consumo_mensual_kwh'))
        costo_total_mensual = sum(dispositivos.mapped('costo_mensual'))
        promedio_eficiencia_operativa = (
            sum(dispositivos.mapped('eficiencia_operativa')) / total_dispositivos if total_dispositivos > 0 else 0
        )

        # Alertas pendientes relacionadas con dispositivos
        alertas_pendientes = self.env['electric.asset.management.alerta'].search_count([
            ('id_dispositivo', 'in', dispositivos.ids),
            ('estado', '=', 'pendiente')
        ])

        # Distribución de dispositivos por estado
        distribucion_por_estado = {
            dict(dispositivos._fields['estado'].selection)[estado]: len(dispositivos.filtered(lambda d: d.estado == estado))
            for estado in dict(dispositivos._fields['estado'].selection).keys()
        }

        # Retornar datos estructurados
        return {
            'kpi': {
                'equipos_criticos': equipos_criticos,
                'consumo_total_mensual': round(consumo_total_mensual, 2),
                'costo_total_mensual': round(costo_total_mensual, 2),
                'promedio_eficiencia_operativa': round(promedio_eficiencia_operativa, 2),
                'alertas_pendientes': alertas_pendientes,
            },
            'graficos': {
                'por_estado': distribucion_por_estado,
            },
        }

    @api.model
    def get_dashboard_data_dispositivo(self):
        """
        Metodo publico para hacer llamado al front end
        este metodo actua como puente para poder acceder a los datos calculados
        """
        return self.data_dispositivo_dashboard()