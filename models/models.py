import logging
from odoo import models, fields, api, tools, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class Zona(models.Model):
    _name = 'electric.asset.management.zona'
    _description = 'Zonas de la empresa'

    name = fields.Char(string='Nombre', required=True)
    description = fields.Text(string='Descripción')
    ubicacion = fields.Char(string='Ubicación')
    fecha_registro = fields.Datetime(string='Fecha de Registro', default=fields.Datetime.now)
    objetivo_reduccion = fields.Float(string='Objetivo de Reducción (%)', help="Objetivo de reducción de consumo energético según ISO 50001")
    consumo_referencia = fields.Float(string='Consumo de Referencia (kWh)', help="Consumo base para comparar mejoras")
    area_m2 = fields.Float(string='Área (m²)', help="Área de la zona para calcular intensidad energética")
    intensidad_energetica = fields.Float(string='Intensidad Energética (kWh/m²)', compute='_compute_intensidad_energetica', store=True)
    
    # Campos para ISO 50001
    es_area_critica = fields.Boolean(string='Área Crítica', help="Áreas con mayor consumo energético según análisis ISO 50001")
    responsable_energia = fields.Many2one('electric.asset.management.usuario', string='Responsable Energía')
    ultima_auditoria = fields.Date(string='Última Auditoría Energética')
    proxima_auditoria = fields.Date(string='Próxima Auditoría Energética')
    observaciones_energia = fields.Text(string='Observaciones Energéticas')
    
    @api.depends('consumo_referencia', 'area_m2')
    def _compute_intensidad_energetica(self):
        for zona in self:
            if zona.area_m2 > 0:
                zona.intensidad_energetica = zona.consumo_referencia / zona.area_m2
            else:
                zona.intensidad_energetica = 0.0


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
            self.contacto_responsable = self.id_usuario.correo
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


class Medicion(models.Model):
    _name = 'electric.asset.management.medicion'
    _description = 'Mediciones de los dispositivos'

    id_dispositivo = fields.Many2one('electric.asset.management.dispositivo', string='Dispositivo')
    fecha_hora = fields.Datetime(string='Fecha y Hora')
    consumo = fields.Float(string='Consumo')
    estado_dispositivo = fields.Selection([
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
        ('En Mantenimiento', 'En Mantenimiento'),
        ('Fuera de Servicio', 'Fuera de Servicio')
    ], string="Estado del dispositivo")
    observaciones = fields.Text(string='Observaciones')
    
    # Campos para ISO 50001
    temperatura_ambiente = fields.Float(string='Temperatura Ambiente (°C)')
    humedad_relativa = fields.Float(string='Humedad Relativa (%)')
    factor_potencia = fields.Float(string='Factor de Potencia')
    desviacion_estandar = fields.Float(string='Desviación Estándar', compute='_compute_desviacion_estandar')
    es_medicion_atipica = fields.Boolean(string='Medición Atípica', compute='_compute_medicion_atipica')
    
    @api.depends('consumo')
    def _compute_desviacion_estandar(self):
        for medicion in self:
            if medicion.id_dispositivo:
                # Obtener mediciones recientes del mismo dispositivo
                mediciones = self.search([
                    ('id_dispositivo', '=', medicion.id_dispositivo.id),
                    ('fecha_hora', '>=', fields.Datetime.to_string(datetime.now() - timedelta(days=30)))
                ], limit=100)
                
                consumos = mediciones.mapped('consumo')
                if len(consumos) > 1:
                    mean = sum(consumos) / len(consumos)
                    variance = sum((x - mean) ** 2 for x in consumos) / len(consumos)
                    medicion.desviacion_estandar = variance ** 0.5
                else:
                    medicion.desviacion_estandar = 0.0
            else:
                medicion.desviacion_estandar = 0.0
    
    @api.depends('consumo', 'desviacion_estandar')
    def _compute_medicion_atipica(self):
        for medicion in self:
            if medicion.id_dispositivo and medicion.desviacion_estandar > 0:
                # Obtener consumo promedio
                mediciones = self.search([
                    ('id_dispositivo', '=', medicion.id_dispositivo.id),
                    ('fecha_hora', '>=', fields.Datetime.to_string(datetime.now() - timedelta(days=30)))
                ], limit=100)
                
                if mediciones:
                    consumos = mediciones.mapped('consumo')
                    mean = sum(consumos) / len(consumos)
                    # Considerar atípico si está a más de 2 desviaciones estándar
                    medicion.es_medicion_atipica = abs(medicion.consumo - mean) > 2 * medicion.desviacion_estandar
                else:
                    medicion.es_medicion_atipica = False
            else:
                medicion.es_medicion_atipica = False
    
    @api.model
    def create(self, vals):
        medicion = super(Medicion, self).create(vals)
        
        # Verificar si es una medición atípica y generar alerta
        if medicion.es_medicion_atipica and medicion.id_dispositivo:
            alerta_vals = {
                'id_dispositivo': medicion.id_dispositivo.id,
                'tipo_alerta': 'advertencia',
                'descripcion': _("Medición atípica registrada para %s: %.2f W (promedio: %.2f W ± %.2f W)") % 
                              (medicion.id_dispositivo.name, medicion.consumo, 
                               sum(medicion.id_dispositivo.medicion_ids.mapped('consumo')) / 
                               len(medicion.id_dispositivo.medicion_ids) if medicion.id_dispositivo.medicion_ids else 0,
                               medicion.desviacion_estandar),
                'prioridad': 'media',
                'responsable': medicion.id_dispositivo.id_usuario.id
            }
            self.env['electric.asset.management.alerta'].create(alerta_vals)
        
        return medicion


class Alerta(models.Model):
    _name = 'electric.asset.management.alerta'
    _description = 'Alertas de los dispositivos'

    id_dispositivo = fields.Many2one('electric.asset.management.dispositivo', string='Dispositivo')
    tipo_alerta = fields.Selection([
        ('critica', 'Crítica'),
        ('advertencia', 'Advertencia'),
        ('informacional', 'Informacional')
    ], string='Tipo de Alerta', required=True)
    descripcion = fields.Text(string='Descripción')
    fecha_hora = fields.Datetime(string='Fecha y Hora', default=fields.Datetime.now)
    estado = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('resuelta', 'Resuelta')
    ], string='Estado de la Alerta', default='pendiente')
    prioridad = fields.Selection([
        ('alta', 'Alta'),
        ('media', 'Media'),
        ('baja', 'Baja')
    ], string='Prioridad', default='media')
    acciones_tomadas = fields.Text(string='Acciones Tomadas')
    responsable = fields.Many2one('electric.asset.management.usuario', string='Responsable')
    fecha_resolucion = fields.Datetime(string='Fecha de Resolución')
    
    # Campos para ISO 50001
    categoria = fields.Selection([
        ('consumo', 'Exceso de Consumo'),
        ('eficiencia', 'Baja Eficiencia'),
        ('mantenimiento', 'Mantenimiento Requerido'),
        ('calibracion', 'Necesita Calibración'),
        ('seguridad', 'Problema de Seguridad')
    ], string='Categoría')
    impacto_energetico = fields.Selection([
        ('alto', 'Alto'),
        ('medio', 'Medio'),
        ('bajo', 'Bajo')
    ], string='Impacto Energético')
    recomendaciones = fields.Text(string='Recomendaciones', compute='_compute_recomendaciones')
    
    @api.depends('categoria', 'id_dispositivo')
    def _compute_recomendaciones(self):
        for alerta in self:
            recomendaciones = []
            
            if alerta.categoria == 'consumo':
                recomendaciones.append(_("Verificar configuración del equipo."))
                recomendaciones.append(_("Evaluar horario de uso para reducir consumo."))
                if alerta.id_dispositivo and alerta.id_dispositivo.modo_bajo_consumo:
                    recomendaciones.append(_("Asegurar que el modo bajo consumo esté activado."))
            
            elif alerta.categoria == 'eficiencia':
                recomendaciones.append(_("Realizar mantenimiento preventivo."))
                recomendaciones.append(_("Verificar calibración del equipo."))
                recomendaciones.append(_("Considerar reemplazo por modelo más eficiente."))
            
            elif alerta.categoria == 'mantenimiento':
                recomendaciones.append(_("Programar mantenimiento según manual del fabricante."))
                recomendaciones.append(_("Verificar filtros y componentes críticos."))
            
            alerta.recomendaciones = "\n".join(recomendaciones) if recomendaciones else _("No hay recomendaciones específicas.")
    
    def action_resolver_alerta(self):
        self.ensure_one()
        self.estado = 'resuelta'
        self.fecha_resolucion = fields.Datetime.now()
        
        # Registrar acción en el dispositivo
        if self.id_dispositivo:
            self.id_dispositivo.message_post(
                body=_("Alerta resuelta: %s\nAcciones tomadas: %s") % 
                     (self.descripcion, self.acciones_tomadas or _("No especificado"))
            )
        
        return True
    
    def action_generar_reporte(self):
        """Genera un reporte a partir de la alerta"""
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


class Usuario(models.Model):
    _name = 'electric.asset.management.usuario'
    _description = 'Usuarios del sistema'

    name = fields.Char(string='Nombre', required=True)
    correo = fields.Char(string='Correo', unique=True)
    rol = fields.Char(string='Rol')
    password = fields.Char(string='Contraseña', password=True)
    fecha_registro = fields.Datetime(string='Fecha de Registro', default=fields.Datetime.now)
    
    # Campos para ISO 50001
    es_auditor_energia = fields.Boolean(string='Auditor de Energía')
    certificaciones = fields.Text(string='Certificaciones Energéticas')
    fecha_ultimo_entrenamiento = fields.Date(string='Último Entrenamiento')
    area_responsable = fields.Many2one('electric.asset.management.zona', string='Área Responsable')


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
    
    # Campos para ISO 50001
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
                # Obtener consumo de referencia para los dispositivos afectados
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
        """Genera un reporte completo según requisitos ISO 50001"""
        self.ensure_one()
        
        if not self.dispositivos_afectados:
            raise UserError(_("Se deben seleccionar dispositivos afectados para generar el reporte ISO 50001."))
        
        # Calcular métricas clave
        zonas = {dispositivo.id_zona for dispositivo in self.dispositivos_afectados if dispositivo.id_zona}
        consumo_referencia = sum(
            dispositivo.consumo_mensual_kwh * 
            ((self.periodo_fin - self.periodo_inicio).days / 30)
            for dispositivo in self.dispositivos_afectados
        )
        reduccion = 100 * (1 - (self.consumo_total / consumo_referencia)) if consumo_referencia > 0 else 0
        
        # Generar contenido del reporte
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
        """Envía el reporte a los responsables"""
        self.ensure_one()
        
        if self.estado != 'generado':
            raise UserError(_("El reporte debe estar en estado 'Generado' para poder enviarse."))
        
        # Obtener destinatarios (responsables de zonas afectadas)
        destinatarios = set()
        for dispositivo in self.dispositivos_afectados:
            if dispositivo.id_zona and dispositivo.id_zona.responsable_energia:
                destinatarios.add(dispositivo.id_zona.responsable_energia.correo)
            elif dispositivo.id_usuario:
                destinatarios.add(dispositivo.id_usuario.correo)
        
        if not destinatarios:
            raise UserError(_("No se encontraron destinatarios para el reporte."))
        
        # Aquí iría la lógica para enviar el correo (usando mail.template o similar)
        # Por simplicidad, solo marcamos como enviado
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