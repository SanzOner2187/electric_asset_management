from odoo import models, fields, api, _
from datetime import datetime

class Dispositivo(models.Model):
    _name = 'electric.asset.management.dispositivo'
    _description = 'Dispositivos de la empresa'

    name = fields.Char(string='Nombre', required=True)
    tipo = fields.Char(string='Tipo')
    marca = fields.Char(string='Marca')
    modelo = fields.Char(string='Modelo')
    consumo_energetico = fields.Float(string='Consumo Energético (Watts)')
    id_zona = fields.Many2one('electric.asset.management.zona', string='Zona')
    estado = fields.Selection([
        ('Buenas Condiciones', 'Buenas Condiciones'),
        ('Aceptable', 'Aceptable'),
        ('Necesita revisión', 'Necesita revisión'),
        ('Necesita Reparación', 'Necesita Reparación'),
        ('Mantenimiento', 'Mantenimiento'),
        ('Dado de baja', 'Dado de baja')
        ], string="Estado del dispositivo")
    fecha_registro = fields.Datetime(string='Fecha de Registro', default=fields.Datetime.now)
    vida_util_estimada = fields.Integer(string='Vida Útil Estimada')
    cumple_estandar = fields.Boolean(string='Cumple Estándar')

    # Nuevos campos
    numero_serie = fields.Char(string='Número de Serie')
    horas_uso_diario = fields.Float(string='Horas de Uso Diario')
    dias_uso_semana = fields.Integer(string='Días de Uso por Semana')
    consumo_diario_kwh = fields.Float(string='Consumo Diario (kWh)', compute='_calcular_consumo_diario', store=True)
    consumo_mensual_kwh = fields.Float(string='Consumo Mensual (kWh)', compute='_calcular_consumo_mensual', store=True)
    costo_kwh = fields.Float(string='Costo por kWh')
    costo_diario = fields.Float(string='Costo Diario', compute='_calcular_costo_diario', store=True)
    costo_mensual = fields.Float(string='Costo Mensual', compute='_calcular_costo_mensual', store=True)
    modo_bajo_consumo = fields.Boolean(string='Modo de Bajo Consumo')
    potencia_bajo_consumo = fields.Float(string='Potencia en Bajo Consumo (Watts)')
    fecha_ultima_revision = fields.Datetime(string='Fecha de Última Revisión')
    id_usuario = fields.Many2one('electric.asset.management.usuario', string='Responsable')
    contacto_responsable = fields.Char(string='Contacto del Responsable')
    fuente_alimentacion = fields.Selection([
        ('ups', 'UPS'),
        ('regulador', 'Regulador'),
        ('directa', 'Directa a la Red')
    ], string='Fuente de Alimentación')
    etiqueta_eficiencia = fields.Selection([
        ('a++', 'A++'),
        ('a+', 'A+'),
        ('a', 'A'),
        ('b', 'B'),
        ('c', 'C'),
        ('d', 'D')
    ], string='Etiqueta de Eficiencia Energética')
    
    # Campos para ISO 50001
    es_equipo_critico = fields.Boolean(string='Equipo Crítico', help="Equipos con mayor consumo según análisis ISO 50001")
    umbral_alerta_consumo = fields.Float(string='Umbral de Alerta (Watts)', help="Consumo máximo permitido antes de generar alerta")
    fecha_calibracion = fields.Date(string='Fecha de Calibración')
    proxima_calibracion = fields.Date(string='Próxima Calibración')
    eficiencia_operativa = fields.Float(
        string='Eficiencia Operativa (%)', 
        compute='_compute_eficiencia_operativa',
        store=True,  # Cambiar a True para almacenarlo
        readonly=True,
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

    @api.depends('consumo_energetico', 'potencia_bajo_consumo', 'modo_bajo_consumo')
    def _compute_eficiencia_operativa(self):
        for dispositivo in self:
            if dispositivo.consumo_energetico > 0:
                if dispositivo.modo_bajo_consumo and dispositivo.potencia_bajo_consumo > 0:
                    dispositivo.eficiencia_operativa = 100 * (1 - (dispositivo.potencia_bajo_consumo / dispositivo.consumo_energetico))
                else:
                    # Comparar con valores estándar según tipo de dispositivo
                    dispositivo.eficiencia_operativa = self._get_eficiencia_estandar(dispositivo.tipo)
            else:
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
            
            # Recomendaciones basadas en eficiencia energética
            if dispositivo.etiqueta_eficiencia in ['c', 'd']:
                recomendaciones.append(_("Considerar reemplazo por equipo con mejor etiqueta de eficiencia (A o B)."))
            
            if dispositivo.eficiencia_operativa < 75.0:
                recomendaciones.append(_("Eficiencia operativa baja. Verificar mantenimiento y calibración."))
            
            if dispositivo.modo_bajo_consumo and dispositivo.horas_uso_diario > 8:
                recomendaciones.append(_("Optimizar horario de uso para aprovechar modo bajo consumo."))
            
            if not dispositivo.modo_bajo_consumo and dispositivo.horas_uso_diario > 4:
                recomendaciones.append(_("Evaluar implementación de modo bajo consumo o programación de apagado automático."))
            
            dispositivo.oportunidades_mejora = "\n".join(recomendaciones) if recomendaciones else _("No se detectaron oportunidades de mejora significativas.")
    
    @api.depends('consumo_mensual_kwh', 'horas_uso_diario', 'dias_uso_semana')
    def _compute_enpi(self):
        for dispositivo in self:
            if dispositivo.horas_uso_diario > 0 and dispositivo.dias_uso_semana > 0:
                # Fórmula básica de EnPI (puede personalizarse según necesidades)
                dispositivo.enpi = dispositivo.consumo_mensual_kwh / (dispositivo.horas_uso_diario * dispositivo.dias_uso_semana * 4)
            else:
                dispositivo.enpi = 0.0
    
    @api.constrains('consumo_energetico', 'umbral_alerta_consumo')
    def _check_consumo_energetico(self):
        for dispositivo in self:
            if dispositivo.umbral_alerta_consumo > 0 and dispositivo.consumo_energetico > dispositivo.umbral_alerta_consumo:
                self._generar_alerta_consumo(dispositivo)
    
    def _generar_alerta_consumo(self, dispositivo):
        alerta_vals = {
            'id_dispositivo': dispositivo.id,
            'tipo_alerta': 'critica' if dispositivo.consumo_energetico > dispositivo.umbral_alerta_consumo * 1.2 else 'advertencia',
            'descripcion': _("El dispositivo %s está consumiendo %s W, superando el umbral de %s W") % 
                          (dispositivo.name, dispositivo.consumo_energetico, dispositivo.umbral_alerta_consumo),
            'prioridad': 'alta',
            'responsable': dispositivo.id_usuario.id
        }
        self.env['electric.asset.management.alerta'].create(alerta_vals)
    
    # Método onchange para id_usuario
    @api.onchange('id_usuario')
    def _onchange_id_usuario(self):
        if self.id_usuario:
            # Se usa 'login' (relacionado con el campo 'user_id.login') en lugar de 'correo'
            self.contacto_responsable = self.id_usuario.login
        else:
            self.contacto_responsable = False

    # Métodos de cálculo de consumo
    @api.depends('consumo_energetico', 'horas_uso_diario')
    def _calcular_consumo_diario(self):
        for dispositivo in self:
            dispositivo.consumo_diario_kwh = (dispositivo.consumo_energetico * dispositivo.horas_uso_diario) / 1000

    @api.depends('consumo_diario_kwh', 'dias_uso_semana')
    def _calcular_consumo_mensual(self):
        for dispositivo in self:
            dispositivo.consumo_mensual_kwh = dispositivo.consumo_diario_kwh * dispositivo.dias_uso_semana * 4

    @api.depends('consumo_diario_kwh', 'costo_kwh')
    def _calcular_costo_diario(self):
        for dispositivo in self:
            dispositivo.costo_diario = dispositivo.consumo_diario_kwh * dispositivo.costo_kwh

    @api.depends('consumo_mensual_kwh', 'costo_kwh')
    def _calcular_costo_mensual(self):
        for dispositivo in self:
            dispositivo.costo_mensual = dispositivo.consumo_mensual_kwh * dispositivo.costo_kwh
    
    def action_generar_reporte_eficiencia(self):
        """Genera un reporte de eficiencia energética para el dispositivo"""
        self.ensure_one()
        
        reporte_vals = {
            'tipo_reporte': 'auditoria',
            'contenido': _("Reporte de Eficiencia Energética para %s\n\nEficiencia Operativa: %.2f%%\nEnPI: %.2f\n\nOportunidades de Mejora:\n%s") % 
                        (self.name, self.eficiencia_operativa, self.enpi, self.oportunidades_mejora),
            'dispositivos_afectados': [(4, self.id)],
            'consumo_total': self.consumo_mensual_kwh,
            'costos_asociados': self.costo_mensual,
            'eficiencia_energetica': self.eficiencia_operativa,
            'recomendaciones': self.oportunidades_mejora,
            'estado': 'generado'
        }
        
        return {
            'name': _('Reporte de Eficiencia Energética'),
            'type': 'ir.actions.act_window',
            'res_model': 'electric.asset.management.reporte',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_' + key: val for key, val in reporte_vals.items()}
        }