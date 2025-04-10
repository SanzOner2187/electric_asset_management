from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class Medicion(models.Model):
    _name = 'electric.asset.management.medicion'
    _description = """
    Modelo para registrar mediciones de dispositivos eléctricos.
    Incluye cálculos de KPIs y detección de mediciones atípicas.
    """
    _order = 'fecha_hora desc'  # Ordenar por fecha y hora descendente para facilitar la visualización

    # Relaciones y campos básicos
    id_dispositivo = fields.Many2one(
        'electric.asset.management.dispositivo', 
        string='Dispositivo', 
        required=True, 
        ondelete='cascade'
    )
    zona_id = fields.Many2one(
        'electric.asset.management.zona',
        string = 'Zona',
        required = True,
        ondelete = 'cascade',
        help = "Zona donde se encuentra el dispositivo"
    )
    fecha_hora = fields.Datetime(string='Fecha y Hora', required=True, default=fields.Datetime.now)
    consumo = fields.Float(string='Consumo (kWh)', required=True, help="Consumo energético en kilovatios-hora")
    potencia_aparente = fields.Float(string='Potencia Aparente (kVA)', help="Potencia total suministrada en kVA")
    factor_potencia = fields.Float(
        string='Factor de Potencia', 
        compute='_compute_factor_potencia', 
        store=True, 
        readonly=True,
        help="Factor de potencia calculado automáticamente"
    )    
    estado_dispositivo = fields.Selection(related='id_dispositivo.estado', string="Estado del Dispositivo", readonly=True)
    observaciones = fields.Text(string='Observaciones')

    # Campos para cumplir con ISO 50001
    temperatura_ambiente = fields.Float(string='Temperatura Ambiente (°C)', help="Temperatura ambiental registrada durante la medición")
    humedad_relativa = fields.Float(string='Humedad Relativa (%)', help="Humedad relativa registrada durante la medición")

    # Indicadores clave de rendimiento (KPIs)
    desviacion_estandar = fields.Float(
        string='Desviación Estándar', 
        compute='_compute_kpis', 
        store=True, 
        readonly=True,
        help="Desviación estándar del consumo energético en comparación con mediciones recientes"
    )
    es_medicion_atipica = fields.Boolean(
        string='¿Atípica?', 
        compute='_compute_kpis', 
        store=True, 
        readonly=True,
        help="Indica si la medición es atípica en comparación con el historial reciente"
    )

    @api.depends('consumo', 'id_dispositivo')
    def _compute_kpis(self):
        """Calcula la desviación estándar y determina si la medición es atípica."""
        for medicion in self:
            if medicion.id_dispositivo:
                # Obtener las mediciones anteriores del mismo dispositivo
                mediciones = self.search([
                    ('id_dispositivo', '=', medicion.id_dispositivo.id),
                    ('fecha_hora', '<', medicion.fecha_hora)  # Excluir la medición actual
                ], order='fecha_hora desc', limit=100)  # Limitar a las últimas 100 mediciones

                if len(mediciones) < 2:
                    # No hay suficientes datos para calcular la desviación estándar
                    medicion.desviacion_estandar = 0.0
                    medicion.es_medicion_atipica = False
                    continue

                # Calcular la media y la desviación estándar
                consumos = mediciones.mapped('consumo')
                mean = sum(consumos) / len(consumos)
                variance = sum((x - mean) ** 2 for x in consumos) / len(consumos)
                desviacion_estandar = variance ** 0.5

                # Verificar si la medición es atípica
                umbral_desviacion = medicion.id_dispositivo.umbral_desviacion or 2.0
                medicion.desviacion_estandar = desviacion_estandar
                medicion.es_medicion_atipica = abs(medicion.consumo - mean) > umbral_desviacion * desviacion_estandar
            else:
                medicion.desviacion_estandar = 0.0
                medicion.es_medicion_atipica = False

    @api.model
    def create(self, vals):
        """Crea una nueva medición y genera alertas si es necesario."""
        medicion = super(Medicion, self).create(vals)

        # Recalcular KPIs después de crear la medición
        medicion._compute_kpis()

        # Generar alerta si la medición es atípica
        if medicion.es_medicion_atipica and medicion.id_dispositivo:
            alerta_vals = {
                'id_dispositivo': medicion.id_dispositivo.id,
                'tipo_alerta': 'advertencia',
                'descripcion': _("Medición atípica registrada para %s: %.2f kWh")
                            % (medicion.id_dispositivo.name, medicion.consumo),
                'prioridad': 'media',
                'responsable': medicion.id_dispositivo.id_usuario.id if medicion.id_dispositivo.id_usuario else False
            }
            self.env['electric.asset.management.alerta'].create(alerta_vals)

        return medicion

    @api.depends('consumo', 'potencia_aparente')
    def _compute_factor_potencia(self):
        """Calcula el factor de potencia automáticamente."""
        for medicion in self:
            if medicion.potencia_aparente > 0:
                medicion.factor_potencia = medicion.consumo / medicion.potencia_aparente
            else:
                medicion.factor_potencia = 0.0

    def action_generar_alerta(self):
        """Genera una alerta manual para la medición seleccionada."""
        for medicion in self:
            # Validaciones previas
            if not medicion.es_medicion_atipica:
                raise UserError(_("No se puede generar una alerta porque la medición no es atípica."))

            # Verificar si ya existe una alerta manual para esta medición
            alerta_existente = self.env['electric.asset.management.alerta'].search([
                ('medicion_id', '=', medicion.id),
                ('tipo_alerta', '=', 'manual')
            ], limit=1)
            if alerta_existente:
                raise UserError(_("Ya existe una alerta manual para esta medición."))

            # Validar que el dispositivo tenga un responsable asignado
            if not medicion.id_dispositivo.id_usuario:
                raise UserError(_("No se puede generar la alerta porque el dispositivo no tiene un responsable asignado."))

            # Crear los valores de la alerta
            alerta_vals = {
                'medicion_id': medicion.id,
                'id_dispositivo': medicion.id_dispositivo.id,
                'tipo_alerta': 'manual',
                'descripcion': _("Alerta manual generada para %s: %.2f kWh") 
                            % (medicion.id_dispositivo.name, medicion.consumo),
                'prioridad': 'alta',
                'responsable': medicion.id_dispositivo.id_usuario.id,
                'categoria': 'consumo',  # Categoría basada en el contexto
                'impacto_energetico': 'alto' if medicion.desviacion_estandar > 2.0 else 'medio',  # Impacto energético
                'estado': 'pendiente'
            }

            # Crear la alerta
            try:
                self.env['electric.asset.management.alerta'].create(alerta_vals)
            except Exception as e:
                _logger.error(f"Error al crear la alerta: {e}")
                raise UserError(_("Ocurrió un error al generar la alerta. Por favor, revise los registros del sistema."))

        # Mostrar notificación de éxito
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Alerta Generada'),
                'message': _('Se ha generado una alerta manual correctamente.'),
                'sticky': False,
            }
        }

    @api.constrains('consumo', 'fecha_hora')
    def _check_consumo_fecha(self):
        """Validaciones adicionales."""
        for medicion in self:
            if medicion.consumo < 0:
                raise UserError(_("El consumo no puede ser negativo."))
            if medicion.fecha_hora > fields.Datetime.now():
                raise UserError(_("La fecha y hora no pueden estar en el futuro."))
                
    @api.onchange('id_dispositivo')
    def _onchange_id_dispositivo(self):
        """Asigna valores base desde el dispositivo seleccionado."""
        if self.id_dispositivo:
            self.consumo = self.id_dispositivo.consumo_energetico / 1000  # Convertir de Watts a kWh
            self.potencia_aparente = self.id_dispositivo.potencia_aparente_base

