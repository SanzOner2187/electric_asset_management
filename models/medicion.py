from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class Medicion(models.Model):
    _name = 'electric.asset.management.medicion'
    _description = """
    Modelo para registrar mediciones de dispositivos eléctricos.
    Incluye cálculos de KPIs y detección de mediciones atípicas.
    """
    _order = 'fecha_hora desc'  
    tipo_medicion = fields.Selection([
        ('general', 'Medición General por Zona'),
        ('zona_especifica', 'Medición por Zonas'),
        ('dispositivo', 'Medición de un Dispositivo'),
    ], string="Tipo de Medición", required=True)

    zona_id = fields.Many2one(
        'electric.asset.management.zona',
        string="Zona (General)", 
        ondelete='cascade'
    )

    factura_id = fields.Many2one(
        'account.move',  
        string='Factura Energética',
        help='Factura energética asociada a esta medición.'
    )

    zonas_ids = fields.Many2many(
        'electric.asset.management.zona', 
        'medicion_zona_rel', 
        'medicion_id',       
        'zona_id',            
        string="Zonas (Varias)"
    )

    dispositivos_relacionados = fields.Many2many(
        'electric.asset.management.dispositivo',
        string="Dispositivos Relacionados",
        compute="_compute_dispositivos_relacionados",
        store=False,
        help="Dispositivos relacionados con la zona o zonas seleccionadas."
    )
    objeto_medido_nombre = fields.Char(
        string="Objeto Medido", compute="_compute_objeto_medido_nombre", store=True
    )

    id_dispositivo = fields.Many2one(
        'electric.asset.management.dispositivo', 
        string='Dispositivo', 
        required=True, 
        ondelete='cascade'
    )
    id_zona = fields.Many2one(
        'electric.asset.management.zona',
        string = 'Zona',
        required = True,
        ondelete = 'cascade',
        help = "Zona donde se encuentra el dispositivo"
    )
    zona_dispositivo = fields.Char(
        related='id_zona.name',  
        string="Zona donde se encuentra el dispositivo",
        readonly=True
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
    estado_dispositivo = fields.Selection(related='id_dispositivo.estado', string="Estado del Dispositivo")
    observaciones = fields.Text(string='Observaciones')

    temperatura_ambiente = fields.Float(string='Temperatura Ambiente (°C)', help="Temperatura ambiental registrada durante la medición")
    humedad_relativa = fields.Float(string='Humedad Relativa (%)', help="Humedad relativa registrada durante la medición")

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

    @api.constrains('tipo_medicion', 'zona_id', 'zonas_ids', 'id_dispositivo')
    def _check_referencias_por_tipo(self):
        for rec in self:
            if rec.tipo_medicion == 'general' and not rec.zona_id:
                raise ValidationError("Debe seleccionar una zona para la medición general.")
            if rec.tipo_medicion == 'zona_especifica' and not rec.zonas_ids:
                raise ValidationError("Debe seleccionar al menos una zona para medición por zonas.")
            if rec.tipo_medicion == 'dispositivo' and not rec.id_dispositivo:
                raise ValidationError("Debe seleccionar un dispositivo para la medición por dispositivo.")

    @api.depends('tipo_medicion', 'zona_id', 'zonas_ids', 'dispositivos_zonas')
    def _compute_nombre_objeto_medido(self):
        for rec in self:
            if rec.tipo_medicion == 'general':
                rec.objeto_medido_nombre = rec.zona_id.name or ''
            elif rec.tipo_medicion == 'zona_especifica':
                rec.objeto_medido_nombre = ', '.join(rec.zonas_ids.mapped('name'))
            elif rec.tipo_medicion == 'dispositivo':
                rec.objeto_medido_nombre = rec.dispositivos_zonas.name or ''

    @api.depends('tipo_medicion', 'zona_id', 'zonas_ids', 'id_dispositivo')
    def _compute_objeto_medido_nombre(self):
        for rec in self:
            if rec.tipo_medicion == 'general':
                rec.objeto_medido_nombre = rec.zona_id.name or ''
            elif rec.tipo_medicion == 'zona_especifica':
                rec.objeto_medido_nombre = ', '.join(rec.zonas_ids.mapped('name'))
            elif rec.tipo_medicion == 'dispositivo':
                rec.objeto_medido_nombre = rec.id_dispositivo.name or ''
            else:
                rec.objeto_medido_nombre = ''

    @api.onchange('tipo_medicion', 'zona_id', 'zonas_ids')
    def _onchange_filtrar_dispositivo_por_zonas(self):
        if self.tipo_medicion == 'zona_especifica' and self.zonas_ids:
            return {
                'domain': {
                    'dispositivos_zonas': [('id_zona', 'in', self.zonas_ids.ids)]
                }
            }
        elif self.tipo_medicion == 'general' and self.zona_id:
            return {
                'domain': {
                    'dispositivos_zonas': [('id_zona', '=', self.zona_id.id)]
                }
            }
        return {'domain': {'dispositivos_zonas': []}}


    @api.onchange('tipo_medicion', 'zona_id', 'zonas_ids')
    def _onchange_tipo_medicion(self):
        """
        Actualiza automáticamente los dispositivos y el consumo según el tipo de medición y las zonas seleccionadas.
        """
        if self.tipo_medicion == 'general' and self.zona_id:
            dispositivos = self.env['electric.asset.management.dispositivo'].search([('id_zona', '=', self.zona_id.id)])
            self.id_dispositivo = dispositivos and dispositivos[0].id or False  
            self.consumo = sum(dispositivos.mapped('consumo_energetico')) / 1000  

        elif self.tipo_medicion == 'zona_especifica' and self.zonas_ids:
            dispositivos = self.env['electric.asset.management.dispositivo'].search([('id_zona', 'in', self.zonas_ids.ids)])
            self.id_dispositivo = dispositivos and dispositivos[0].id or False  
            self.consumo = sum(dispositivos.mapped('consumo_energetico')) / 1000  

        elif self.tipo_medicion == 'dispositivo' and self.id_dispositivo:
            self.consumo = self.id_dispositivo.consumo_energetico / 1000  

        else:
            self.id_dispositivo = False
            self.consumo = 0.0

    @api.onchange('tipo_medicion', 'zona_id', 'zonas_ids')
    def _compute_dispositivos_relacionados(self):
        """
        Actualiza los dispositivos relacionados según el tipo de medición y las zonas seleccionadas.
        """
        for rec in self:
            if rec.tipo_medicion == 'general' and rec.zona_id:
                rec.dispositivos_relacionados = self.env['electric.asset.management.dispositivo'].search([
                    ('id_zona', '=', rec.zona_id.id)
                ])
            elif rec.tipo_medicion == 'zona_especifica' and rec.zonas_ids:
                rec.dispositivos_relacionados = self.env['electric.asset.management.dispositivo'].search([
                    ('id_zona', 'in', rec.zonas_ids.ids)
                ])
            else:
                rec.dispositivos_relacionados = False
    @api.depends('consumo', 'id_dispositivo')
    def _compute_kpis(self):
        """Calcula la desviación estándar y determina si la medición es atípica."""
        for medicion in self:
            if medicion.id_dispositivo:
                mediciones = self.search([
                    ('id_dispositivo', '=', medicion.id_dispositivo.id),
                    ('fecha_hora', '<', medicion.fecha_hora)  
                ], order='fecha_hora desc', limit=100)  

                if len(mediciones) < 2:
                    medicion.desviacion_estandar = 0.0
                    medicion.es_medicion_atipica = False
                    continue

                consumos = mediciones.mapped('consumo')
                mean = sum(consumos) / len(consumos)
                variance = sum((x - mean) ** 2 for x in consumos) / len(consumos)
                desviacion_estandar = variance ** 0.5

                umbral_desviacion = medicion.id_dispositivo.umbral_desviacion or 2.0
                medicion.desviacion_estandar = desviacion_estandar
                medicion.es_medicion_atipica = abs(medicion.consumo - mean) > umbral_desviacion * desviacion_estandar
            else:
                medicion.desviacion_estandar = 0.0
                medicion.es_medicion_atipica = False

    @api.model
    def create(self, vals):
        """Sobrescribe el método create para asignar la zona automáticamente."""
        if 'id_dispositivo' in vals and vals['id_dispositivo']:
            dispositivo = self.env['electric.asset.management.dispositivo'].browse(vals['id_dispositivo'])
            vals['id_zona'] = dispositivo.id_zona.id
        medicion = super(Medicion, self).create(vals)

        medicion._compute_kpis()

        if medicion.es_medicion_atipica and medicion.id_dispositivo:
            alerta_vals = {
                'name': _("Medición de consumo anormal: %s (%.2f kWh)") % (medicion.id_dispositivo.name, medicion.consumo),
                'id_dispositivo': medicion.id_dispositivo.id,
                'tipo_alerta': 'advertencia',
                'descripcion': _("Medición atípica registrada para %s: %.2f kWh")
                            % (medicion.id_dispositivo.name, medicion.consumo),
                'prioridad': 'media',
                'responsable': medicion.id_dispositivo.id_usuario.id if medicion.id_dispositivo.id_usuario else False
            }
            self.env['electric.asset.management.alerta'].create(alerta_vals)

        return medicion

    def write(self, vals):
        """Sobrescribe el método write para asignar la zona automáticamente."""
        if 'id_dispositivo' in vals and vals['id_dispositivo']:
            dispositivo = self.env['electric.asset.management.dispositivo'].browse(vals['id_dispositivo'])
            vals['id_zona'] = dispositivo.id_zona.id
        return super(Medicion, self).write(vals)

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
            if not medicion.es_medicion_atipica:
                raise UserError(_("No se puede generar una alerta porque la medición no es atípica."))

            alerta_existente = self.env['electric.asset.management.alerta'].search([
                ('medicion_id', '=', medicion.id),
                ('tipo_alerta', '=', 'manual')
            ], limit=1)
            if alerta_existente:
                raise UserError(_("Ya existe una alerta manual para esta medición."))

            if not medicion.id_dispositivo.id_usuario:
                raise UserError(_("No se puede generar la alerta porque el dispositivo no tiene un responsable asignado."))

            alerta_vals = {
                'name': _("Medición de consumo anormal: %s (%.2f kWh)") % (medicion.id_dispositivo.name, medicion.consumo),
                'medicion_id': medicion.id,
                'id_dispositivo': medicion.id_dispositivo.id,
                'tipo_alerta': 'manual',
                'descripcion': _("Alerta manual generada para %s: %.2f kWh") 
                            % (medicion.id_dispositivo.name, medicion.consumo),
                'prioridad': 'alta',
                'responsable': medicion.id_dispositivo.id_usuario.id,
                'categoria': 'consumo',  
                'impacto_energetico': 'alto' if medicion.desviacion_estandar > 2.0 else 'medio',  
                'estado': 'pendiente'
            }

            try:
                self.env['electric.asset.management.alerta'].create(alerta_vals)
            except Exception as e:
                _logger.error(f"Error al crear la alerta: {e}")
                raise UserError(_("Ocurrió un error al generar la alerta. Por favor, revise los registros del sistema."))

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
        """Actualiza la zona automáticamente al seleccionar un dispositivo."""
        if self.id_dispositivo:
            self.id_zona = self.id_dispositivo.id_zona
            self.consumo = self.id_dispositivo.consumo_energetico / 1000  # Convertir de Watts a kWh
            self.potencia_aparente = self.id_dispositivo.potencia_aparente_base


    def data_medicion_dashboard(self):
        """
        Método para extraer datos clave del modelo Medicion para mostrar en un dashboard.
        """
        mediciones = self.env['electric.asset.management.medicion'].search([])

        total_mediciones = len(mediciones)
        mediciones_atipicas = len(mediciones.filtered(lambda m: m.es_medicion_atipica))
        consumo_promedio = sum(m.consumo for m in mediciones) / total_mediciones if total_mediciones > 0 else 0.0

        mediciones_por_zona = {
            zona.name: len(mediciones.filtered(lambda m: m.id_zona == zona))
            for zona in self.env['electric.asset.management.zona'].search([])
        }

        mediciones_por_dispositivo = {
            dispositivo.name: len(mediciones.filtered(lambda m: m.id_dispositivo == dispositivo))
            for dispositivo in self.env['electric.asset.management.dispositivo'].search([])
        }

        ultimas_mediciones = mediciones.sorted(key=lambda m: m.fecha_hora, reverse=True)[:5]
        ultimas_mediciones_data = [
            {
                'dispositivo': m.id_dispositivo.name or 'Sin dispositivo',
                'zona': m.id_zona.name or 'Sin zona',
                'consumo': m.consumo,
                'fecha': m.fecha_hora.strftime('%Y-%m-%d %H:%M:%S'),
                'atipica': m.es_medicion_atipica,
            }
            for m in ultimas_mediciones
        ]

        return {
            'kpi': {
                'total_mediciones': total_mediciones,
                'mediciones_atipicas': mediciones_atipicas,
                'consumo_promedio': round(consumo_promedio, 2),
            },
            'graficos': {
                'por_zona': mediciones_por_zona,
                'por_dispositivo': mediciones_por_dispositivo,
            },
            'ultimas_mediciones': ultimas_mediciones_data,
        }
    
    @api.model
    def get_dashboard_data_medicion(self):
        """
        Metodo publico para hacer llamado al front end
        este metodo actua como puente para poder acceder a los datos calculados
        """
        return self.data_medicion_dashboard()