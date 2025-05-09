from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class FacturaEnergetica(models.Model):
    _name = 'electric.asset.management.factura.energetica'
    _description = 'Factura Energética'
    _rec_name = 'referencia_factura'

    # Campos básicos
    referencia_factura = fields.Char(string='Referencia de Factura', required=True)
    proveedor_id = fields.Many2one('res.partner', string='Proveedor', required=True, help="Proveedor de energía.")
    factura_contable_id = fields.Many2one('account.move', string='Factura Contable', help="Factura contable asociada.")
    zonas_consumo_ids = fields.Many2many(
        'electric.asset.management.zona', 
        'factura_zona_rel',
        'factura_id',
        'zona_id',
        string='Zonas de Consumo', 
        required=True, 
        help="Zonas donde se registró el consumo."
    )

    # Período de facturación
    periodo_inicio = fields.Date(string='Fecha de Inicio del Período', required=True)
    periodo_fin = fields.Date(string='Fecha de Fin del Período', required=True)
    dias_facturados = fields.Integer(string='Días Facturados', compute='_compute_dias_facturados', store=True)

    # Consumo y costos
    consumo_diario = fields.Float(string='Consumo Diario (kWh)', required=True, help="Consumo promedio diario en kWh.")
    costo_diario = fields.Float(string='Costo Diario ($)', required=True, help="Costo promedio diario en la factura.")
    consumo_mensual_estimado = fields.Float(string='Consumo Mensual Estimado (kWh)', required=True, help="Consumo mensual estimado en kWh.")
    consumo_total = fields.Float(string='Consumo Total (kWh)', required=True, help="Consumo total de energía en el período.")
    subtotal = fields.Float(string='Subtotal ($)', required=True, help="Subtotal de la factura.")
    total_pagar = fields.Float(string='Total a Pagar ($)', required=True, help="Monto total a pagar en la factura.")
    fecha_proxima_factura = fields.Date(string='Fecha Estimada de Próxima Factura', help="Fecha estimada para la próxima factura.")
    promedio_6_meses = fields.Float(string='Promedio de Consumo Últimos 6 Meses (kWh)', help="Consumo promedio de los últimos 6 meses.")

    # Archivo de factura
    archivo_factura = fields.Binary(string='Archivo de Factura', help="Archivo digital de la factura.")
    nombre_archivo = fields.Char(string='Nombre del Archivo', help="Nombre del archivo de la factura.")

    # Consumo del sistema y diferencias
    consumo_registro_sistema = fields.Float(string='Consumo Registrado por Sistema (kWh)', required=True, help="Consumo registrado por el sistema en el período.")
    diferencia_consumo = fields.Float(string='Diferencia de Consumo (kWh)', compute='_compute_diferencias', store=True, help="Diferencia entre el consumo facturado y el registrado por el sistema.")
    diferencia_costo_estimado = fields.Float(string='Diferencia Estimada de Costo ($)', compute='_compute_diferencias', store=True, help="Diferencia estimada de costos entre la factura y el sistema.")
    dispositivos_relacionados = fields.Many2many(
        'electric.asset.management.dispositivo',
        string="Dispositivos Relacionados",
        compute="_compute_dispositivos_relacionados",
        store=False,
        help="Dispositivos relacionados con la zona de la factura."
    )
    # Métodos computados
    @api.onchange('zonas_consumo_ids')
    def _compute_dispositivos_relacionados(self):
        """
        Actualiza los dispositivos relacionados según el tipo de medición y las zonas seleccionadas.
        """
        for rec in self:
            if  rec.zonas_consumo_ids:
                rec.dispositivos_relacionados = self.env['electric.asset.management.dispositivo'].search([
                    ('id_zona', '=', rec.zonas_consumo_ids.id)
                ])
            else:
                rec.dispositivos_relacionados = False

    @api.depends('periodo_inicio', 'periodo_fin')
    def _compute_dias_facturados(self):
        """Calcula los días facturados en el período."""
        for record in self:
            if record.periodo_inicio and record.periodo_fin:
                if record.periodo_fin < record.periodo_inicio:
                    raise ValidationError(_('La fecha fin no puede ser anterior a la fecha inicio.'))
                delta = record.periodo_fin - record.periodo_inicio
                record.dias_facturados = delta.days + 1
            else:
                record.dias_facturados = 0

    @api.depends('consumo_total', 'consumo_registro_sistema', 'total_pagar')
    def _compute_diferencias(self):
        """Calcula las diferencias de consumo y costo."""
        for record in self:
            record.diferencia_consumo = record.consumo_total - record.consumo_registro_sistema
            if record.consumo_total:
                costo_sistema = (record.consumo_registro_sistema / record.consumo_total) * record.total_pagar
                record.diferencia_costo_estimado = record.total_pagar - costo_sistema
            else:
                record.diferencia_costo_estimado = 0.0

    # Validaciones
    @api.constrains('periodo_inicio', 'periodo_fin')
    def _check_fechas(self):
        """Valida que las fechas del período sean coherentes."""
        for record in self:
            if record.periodo_fin < record.periodo_inicio:
                raise ValidationError(_('La fecha fin no puede ser anterior a la fecha inicio.'))

    @api.constrains('consumo_diario', 'costo_diario', 'consumo_total', 'total_pagar')
    def _check_valores_positivos(self):
        """Valida que los valores de consumo y costos sean positivos."""
        for record in self:
            if record.consumo_diario < 0 or record.costo_diario < 0 or record.consumo_total < 0 or record.total_pagar < 0:
                raise ValidationError(_('Los valores de consumo y costos deben ser positivos.'))

    # Métodos adicionales
    def action_validar_factura(self):
        """Método para validar la factura."""
        for record in self:
            if not record.factura_contable_id:
                raise ValidationError(_('Debe asociar una factura contable antes de validar.'))
            if record.diferencia_consumo > 0:
                raise ValidationError(_('La diferencia de consumo es mayor a cero. Revise los datos antes de validar.'))
            record.message_post(body=_('Factura validada correctamente.'))

    def action_generar_reporte(self):
        """Genera un reporte detallado de la factura."""
        return {
            'type': 'ir.actions.report',
            'report_name': 'electric_asset_management.factura_energetica_report',
            'report_type': 'qweb-pdf',
            'context': {'active_ids': self.ids},
        }