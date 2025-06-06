from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

class Zona(models.Model):
    _name = 'electric.asset.management.zona'
    _description = 'Zonas de la empresa'
    _order = 'name'  
    _parent_name = 'zona_padre'  # campo que define la relacion padre - hijo
    _parent_store = True  # habilita almacenamiento de jerarquia 
    _rec_name = 'complete_name'  # usa nombre completo para jerarquia

    name = fields.Char(string='Nombre', required=True, tracking=True, help="Nombre identificativo de la zona según ISO 50001")
    complete_name = fields.Char(string='Nombre Completo', compute='_compute_complete_name', store=True, help="Nombre completo que incluye la jerarquía de zonas")
    description = fields.Text(string='Descripción',tracking=True, help="Descripción detallada de la zona para facilitar su identificación")
    ubicacion = fields.Char(string='Ubicación', required=True, help="Ubicación física de la zona dentro de la empresa")
    fecha_registro = fields.Datetime(string='Fecha de Registro', default=fields.Datetime.now, readonly=True, help="Fecha en la que se registró la zona")
    objetivo_reduccion = fields.Float(string='Objetivo de Reducción (%)',help="Objetivo de reducción de consumo energético según ISO 50001",tracking=True)
    consumo_referencia = fields.Float(string='Consumo de Referencia (kWh)', help="Consumo base para comparar mejoras energéticas", tracking=True)
    area_m2 = fields.Float(string='Área (m²)',help="Área de la zona para calcular intensidad energética", tracking=True)
    intensidad_energetica = fields.Float(string='Intensidad Energética (kWh/m²)', compute='_compute_intensidad_energetica', store=True, help="Indicador clave de rendimiento energético según ISO 50001",digits=(10, 4))
    es_area_critica = fields.Boolean(string='Área Crítica', help="Zonas con mayor consumo energético según análisis ISO 50001", tracking=True)
    responsable_energia = fields.Many2one('res.users', string='Responsable Energía', help="Persona encargada de gestionar la energía en esta zona")
    ultima_auditoria = fields.Date(string='Última Auditoría Energética',help="Fecha de la última auditoría energética realizada en esta zona")
    proxima_auditoria = fields.Date(string='Próxima Auditoría Energética',help="Fecha programada para la próxima auditoría energética")
    zona_padre = fields.Many2one('electric.asset.management.zona', string='Zona Padre', ondelete='restrict', help="Zona principal a la que pertenece esta subzona")
    subzonas = fields.One2many('electric.asset.management.zona','zona_padre', string='Subzonas', help="Lista de subzonas que dependen de esta zona")
    parent_path = fields.Char(index=True, help="Campo interno para manejar la jerarquía de zonas")
    dispositivos_ids = fields.One2many('electric.asset.management.dispositivo', 'id_zona', string='Dispositivos', help="Dispositivos asociados a esta zona")
    mediciones_ids = fields.One2many('electric.asset.management.medicion', 'id_zona', string='Mediciones', help="Mediciones asociadas a esta zona")
    alertas_ids = fields.One2many('electric.asset.management.alerta', 'zona_id', string='Alertas', help="Alertas asociadas a esta zona")
    reportes_ids = fields.One2many('electric.asset.management.reporte', 'zona_id', string='Reportes', help="Reportes asociados a esta zona")

    @api.depends('name', 'zona_padre.complete_name')
    def _compute_complete_name(self):
        """
        Calcula el nombre completo de la zona incluyendo la jerarquía.
        Ejemplo: "Primer Piso / Mostrador"
        """
        for zona in self:
            if zona.zona_padre:
                zona.complete_name = f"{zona.zona_padre.complete_name} / {zona.name}"
            else:
                zona.complete_name = zona.name

    @api.depends('consumo_referencia', 'area_m2')
    def _compute_intensidad_energetica(self):
        """
        Calcula la intensidad energética (kWh/m²).
        Se manejan casos especiales para evitar divisiones por cero.
        """
        for zona in self:
            if zona.area_m2 > 0:
                zona.intensidad_energetica = zona.consumo_referencia / zona.area_m2
            else:
                zona.intensidad_energetica = 0.0

    @api.constrains('objetivo_reduccion')
    def _check_objetivo_reduccion(self):
        """
        Validación para asegurar que el objetivo de reducción esté dentro de un rango lógico.
        """
        for zona in self:
            if zona.objetivo_reduccion < 0 or zona.objetivo_reduccion > 100:
                raise ValidationError(_("El objetivo de reducción debe estar entre 0% y 100%."))

    @api.constrains('area_m2')
    def _check_area_m2(self):
        """
        Validación para asegurar que el área no sea negativa.
        """
        for zona in self:
            if zona.area_m2 < 0:
                raise ValidationError(_("El área no puede ser negativa."))

    @api.constrains('consumo_referencia')
    def _check_consumo_referencia(self):
        """
        Validación para asegurar que el consumo de referencia no sea negativo.
        """
        for zona in self:
            if zona.consumo_referencia < 0:
                raise ValidationError(_("El consumo de referencia no puede ser negativo."))

    @api.onchange('ultima_auditoria')
    def _onchange_ultima_auditoria(self):
        """
        Sugerir automáticamente la próxima auditoría basada en la última auditoría.
        """
        if self.ultima_auditoria:
            self.proxima_auditoria = self.ultima_auditoria + relativedelta(years=1)

    def action_schedule_audit(self):
        """
        Acción para programar una auditoría energética.
        Puede extenderse para enviar notificaciones o crear actividades.
        """
        self.ensure_one()
        return {
            'name': _('Programar Auditoría'),
            'type': 'ir.actions.act_window',
            'res_model': 'electric.asset.management.audit.wizard',
            'view_mode': 'form',
            'target': 'new',
        }
    
    @api.constrains('zona_padre')
    def _check_circular_reference(self):
        for zona in self:
            if zona.zona_padre:
                current = zona.zona_padre
                while current:
                    if current == zona:
                        raise ValidationError(_("No se permite una referencia circular en la jerarquía de zonas."))
                    current = current.zona_padre

    def data_zona_dashboard(self):
        """
        Método para extraer datos clave del modelo Zona para mostrar en un dashboard.
        """
        zonas = self.env['electric.asset.management.zona'].search([])

        total_zonas = len(zonas)
        areas_criticas = len(zonas.filtered(lambda z: z.es_area_critica))
        intensidad_energetica_promedio = sum(z.intensidad_energetica for z in zonas) / total_zonas if total_zonas > 0 else 0.0

        fecha_actual = fields.Date.today()
        proximas_auditorias = zonas.filtered(lambda z: z.proxima_auditoria and z.proxima_auditoria <= fecha_actual + relativedelta(days=30))
        zonas_proximas_auditorias = len(proximas_auditorias)

        zonas_por_intensidad = {
            'baja': len(zonas.filtered(lambda z: z.intensidad_energetica < 50)),
            'media': len(zonas.filtered(lambda z: 50 <= z.intensidad_energetica < 150)),
            'alta': len(zonas.filtered(lambda z: z.intensidad_energetica >= 150)),
        }

        return {
            'kpi': {
                'total_zonas': total_zonas,
                'areas_criticas': areas_criticas,
                'intensidad_energetica_promedio': round(intensidad_energetica_promedio, 2),
                'zonas_proximas_auditorias': zonas_proximas_auditorias,
            },
            'graficos': {
                'por_intensidad': zonas_por_intensidad,
            },
        }

    @api.model
    def get_dashboard_data_zona(self):
        """
        Metodo publico para hacer llamado al front end
        este metodo actua como puente para poder acceder a los datos calculados
        """
        return self.data_zona_dashboard()