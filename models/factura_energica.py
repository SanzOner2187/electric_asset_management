from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class FacturaEnergetica(models.Model):
    _description = 'Factura Energética'
    _inherit = 'account.move'

    factura_id = fields.Many2one(
        'account.move', 
        string='Factura Energética',
        help='Factura energética asociada a esta medición.'
    )

    factura_energetica = fields.Boolean(
        string='¿Es una factura energética?',
        help='Determina si es una factura energética para activar alertas si las hay',
        default=False
    )

    # relaciones 
    zonas_consumo_ids = fields.Many2many(
        'electric.asset.management.zona',
        'factura_zona_rel',
        'factura_id',
        'zona_id',
        string='Zonas de Consumo',
        required=True,
        help="Zonas donde se registró el consumo."
    )

    dispositivos_ids = fields.Many2many(
        'electric.asset.management.dispositivo',
        'factura_dispositivo_rel',
        'factura_id',
        'dispositivo_id',
        string='Dispositivos Asociados',
        help="Dispositivos cuyo consumo se refleja en esta factura.",
        readonly=True
    )


    # datos de energia
    consumo_total_usuario = fields.Float(
        string='Consumo Total De la Factura (kWh)',
        required=True,
        help="Consumo total de energía ingresado por el usuario."
    )

    consumo_total_sistema = fields.Float(
        string='Consumo Total Sistema (kWh)',
        compute='_compute_consumo_total_sistema',
        store=True,
        help="Consumo total calculado automáticamente basado en los dispositivos asociados."
    )

    costo_total_usuario = fields.Float(
        string='Costo Total de la factura (COP)',
        required=True,
        help="Costo total ingresado por el usuario con datos de la factura"
    )

    costo_total_sistema = fields.Float(
        string='Costo Total Registrado por el sistema ($)',
        compute='_compute_costo_total_sistema',
        store=True,
        help="Costo total calculado automáticamente basado en los dispositivos asociados."
    )

    diferencia_consumo = fields.Float(
        string='Diferencia de Consumo (kWh)',
        compute='_compute_diferencias',
        store=True,
        help="Diferencia entre el consumo ingresado por el usuario y el calculado por el sistema."
    )

    diferencia_costo = fields.Float(
        string='Diferencia de Costo (COP)',
        compute='_compute_diferencias',
        store=True,
        help="Diferencia entre el costo ingresado por el usuario y el calculado por el sistema."
    )

    total_pagar = fields.Float(
        string='Total a Pagar (COP)',
        required=True,
        help="Monto total a pagar en la factura."
    )

    archivo_factura = fields.Binary(string='Archivo de Factura', help="Archivo digital de la factura.")

    # campos calculados
    consumo_diario = fields.Float(
        string='Consumo Diario (kWh)',
        compute='_calcular_consumo_diario',
        store=True
    )

    costo_diario = fields.Float(
        string='Costo Diario ($)',
        compute='_calcular_costo_diario',
        store=True
    )

    eficiencia_global = fields.Float(
        string='Eficiencia Global (%)',
        compute='_calcular_eficiencia_global',
        store=True,
        help="Eficiencia promedio de los dispositivos asociados"
    )

    # Cálculo actualizado del total a pagar según el sistema
    total_pagar_sistema = fields.Float(
        string='Total a Pagar (Sistema) ($)',
        compute='_calcular_total_pagar_sistema',
        store=True,
        help="Monto total a pagar calculado según el consumo de las zonas y dispositivos asociados."
    )

    @api.depends('zonas_consumo_ids')
    def _compute_costo_total_sistema(self):
        """
        Calcular el costo total basado en los dispositivos asociados a las zonas seleccionadas.
        """
        for factura in self:
            # Buscar dispositivos relacionados con las zonas seleccionadas
            dispositivos = self.env['electric.asset.management.dispositivo'].search([
                ('id_zona', 'in', factura.zonas_consumo_ids.ids)
            ])
            # Sumar el costo mensual de todos los dispositivos
            factura.costo_total_sistema = sum(dispositivo.costo_mensual for dispositivo in dispositivos)

    @api.constrains('factura_energetica', 'zonas_consumo_ids', 'consumo_total_usuario', 'dispositivos_ids')
    def _check_datos_factura(self):
        """
        Validar que los datos de la factura sean consistentes.
        """
        for factura in self:
            if factura.factura_energetica:
                if not factura.zonas_consumo_ids:
                    raise ValidationError(_("Debe seleccionar al menos una zona de consumo."))
                if factura.consumo_total_usuario <= 0:
                    raise ValidationError(_("El consumo total ingresado por el usuario debe ser mayor a cero."))
                if not factura.dispositivos_ids:
                    raise ValidationError(_("Debe asociar al menos un dispositivo a la factura."))
                    
    @api.onchange('zonas_consumo_ids')
    def _onchange_zonas_consumo_ids(self):
        """
        Al cambiar las zonas seleccionadas, actualizar los dispositivos asociados
        y calcular el consumo total de los dispositivos de esas zonas.
        """
        for factura in self:
            # Obtener dispositivos asociados a las zonas seleccionadas
            dispositivos = self.env['electric.asset.management.dispositivo'].search([
                ('id_zona', 'in', factura.zonas_consumo_ids.ids)
            ])
            factura.dispositivos_ids = dispositivos

            # Calcular el consumo total de los dispositivos de las zonas seleccionadas
            consumo_total_zonas = sum(dispositivo.consumo_energetico for dispositivo in dispositivos)
            factura.consumo_total = consumo_total_zonas

    @api.depends('zonas_consumo_ids', 'dispositivos_ids')
    def _compute_alertas_ids(self):
        """
        Filtrar alertas generadas en el período de la factura.
        """
        for factura in self:
            if factura.invoice_date and factura.invoice_date_due:
                alertas = self.env['electric.asset.management.alerta'].search([
                    ('factura_id', '=', factura.id),  # Asegúrate de que 'factura_id' exista en el modelo 'alerta'
                    ('fecha_alerta', '>=', factura.invoice_date),
                    ('fecha_alerta', '<=', factura.invoice_date_due)
                ])
                factura.alertas_ids = alertas
            else:
                factura.alertas_ids = False

    @api.depends('zonas_consumo_ids', 'dispositivos_ids')
    def _compute_reportes_ids(self):
        """
        Filtrar reportes generados en el período de la factura.
        """
        for factura in self:
            if factura.invoice_date and factura.invoice_date_due:
                reportes = self.env['electric.asset.management.reporte'].search([
                    ('zona_id', 'in', factura.zonas_consumo_ids.ids),
                    ('fecha_reporte', '>=', factura.invoice_date),
                    ('fecha_reporte', '<=', factura.invoice_date_due)
                ])
                factura.reportes_ids = reportes
            else:
                factura.reportes_ids = False

    @api.depends('zonas_consumo_ids')
    def _compute_consumo_total_sistema(self):
        """
        Calcular el consumo total basado en los dispositivos asociados a las zonas seleccionadas.
        """
        for factura in self:
            dispositivos = self.env['electric.asset.management.dispositivo'].search([
                ('id_zona', 'in', factura.zonas_consumo_ids.ids)
            ])
            factura.consumo_total_sistema = sum(dispositivo.consumo_mensual_kwh for dispositivo in dispositivos)

    @api.depends('zonas_consumo_ids')
    def _calcular_total_pagar_sistema(self):
        """
        Calcular el total a pagar basado en el consumo y costo de los dispositivos asociados.
        """
        for factura in self:
            dispositivos = self.env['electric.asset.management.dispositivo'].search([
                ('id_zona', 'in', factura.zonas_consumo_ids.ids)
            ])
            factura.total_pagar_sistema = sum(
                dispositivo.consumo_mensual_kwh * dispositivo.costo_kwh for dispositivo in dispositivos
            )

    @api.depends('consumo_total_usuario', 'consumo_total_sistema', 'costo_total_usuario', 'costo_total_sistema')
    def _compute_diferencias(self):
        """
        Calcular las diferencias entre los valores ingresados por el usuario y los calculados por el sistema.
        """
        for factura in self:
            factura.diferencia_consumo = factura.consumo_total_usuario - factura.consumo_total_sistema
            factura.diferencia_costo = factura.costo_total_usuario - factura.costo_total_sistema


    @api.depends('consumo_total_usuario', 'invoice_date_due', 'invoice_date')
    def _calcular_consumo_diario(self):
        """
        Recalcular el consumo diario basado en el consumo total ingresado por el usuario
        y las fechas de la factura.
        """
        for factura in self:
            dias = 1
            if factura.invoice_date and factura.invoice_date_due:
                dias = (factura.invoice_date_due - factura.invoice_date).days + 1
            factura.consumo_diario = factura.consumo_total_usuario / dias if dias else 0
   
    @api.onchange('zonas_consumo_ids')
    def _onchange_zonas_consumo_ids(self):
        """
        Al cambiar las zonas seleccionadas, actualizar los dispositivos asociados.
        """
        for factura in self:
            dispositivos = self.env['electric.asset.management.dispositivo'].search([
                ('id_zona', 'in', factura.zonas_consumo_ids.ids)
            ])
            factura.dispositivos_ids = dispositivos

    @api.depends('total_pagar', 'invoice_date_due', 'invoice_date')
    def _calcular_costo_diario(self):
        """
        Recalcular el costo diario basado en el total a pagar y las fechas de la factura.
        """
        for factura in self:
            dias = 1
            if factura.invoice_date and factura.invoice_date_due:
                dias = (factura.invoice_date_due - factura.invoice_date).days + 1
            factura.costo_diario = factura.total_pagar / dias if dias else 0


    @api.depends('dispositivos_ids.eficiencia_operativa')
    def _calcular_eficiencia_global(self):
        """
        Recalcular la eficiencia global basada en los dispositivos asociados.
        """
        for factura in self:
            eficiencias = factura.dispositivos_ids.mapped('eficiencia_operativa')
            factura.eficiencia_global = sum(eficiencias) / len(eficiencias) if eficiencias else 0

    # generar alerta
    def generar_alertas_consumo_anormal(self):
        for factura in self:
            for dispositivo in factura.dispositivos_ids:
                if dispositivo.consumo_energetico > dispositivo.umbral_alerta_consumo:
                    self.env['electric.asset.management.alerta'].create({
                        'id_dispositivo': dispositivo.id,
                        'tipo_alerta': 'critica',
                        'descripcion': f"Consumo excesivo en {dispositivo.name}: {dispositivo.consumo_energetico} W",
                        'categoria': 'consumo',
                        'impacto_energetico': 'alto',
                        'factura_id': factura.id,
                        'responsable': dispositivo.id_usuario.id if dispositivo.id_usuario else False
                    })