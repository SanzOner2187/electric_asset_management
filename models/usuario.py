from odoo import models, fields, api, _
from odoo.exceptions import UserError

class Usuario(models.Model):
    _name = 'electric.asset.management.usuario'
    _description = 'Usuarios del sistema'
    _inherits = {'res.users': 'user_id'}

    # Relación con el usuario base de Odoo
    user_id = fields.Many2one('res.users', string='Nombre', required=True, ondelete='cascade')
    login = fields.Char(related='user_id.login', string='Correo', store=True, readonly=False)

    # Roles disponibles
    rol = fields.Selection([
        ('empleado', 'Empleado'),
        ('auditor', 'Auditor Energético'),
        ('administrador', 'Administrador'),
        ('otro', 'Otro')
    ], required = True, string='Rol', help="Rol del usuario en el sistema de gestión energética.")

    # Campos específicos para empleados
    equipo_asignado = fields.Many2one('electric.asset.management.dispositivo', string='Equipo Asignado', help="Equipo asignado al empleado.")

    # Campos específicos para auditores
    es_auditor_energia = fields.Boolean(string='Es Auditor de Energía', help="Indica si el usuario está certificado como auditor energético.")
    certificaciones = fields.Binary(string='Certificaciones Energéticas', help="Certificaciones relevantes para la gestión energética.")
    fecha_ultimo_entrenamiento = fields.Date(string='Último Entrenamiento', help="Fecha del último entrenamiento en gestión energética.")
    dispositivo_a_cargo = fields.Many2many (
        'electric.asset.management.dispositivo', 
        'usuario_dispositivo_rel',
        'usuario_id',
        'dispositivo_id',
        string="Dispositivos a cargo del auditor",
        help="Equipos bajo la supervision y responsabilidad del auditor"
    )
    
    # Validaciones
    @api.constrains('rol', 'es_auditor_energia', 'certificaciones')
    def _check_campos_por_rol(self):
        """Validación: Los campos deben ser consistentes con el rol seleccionado."""
        for record in self:
            if record.rol == 'auditor':
                if not record.es_auditor_energia:
                    raise UserError(_("Un auditor debe estar marcado como 'Es Auditor de Energía'."))
                if not record.certificaciones:
                    raise UserError(_("Un auditor debe proporcionar sus certificaciones."))
            elif record.rol == 'empleado':
                if record.es_auditor_energia or record.certificaciones or record.fecha_ultimo_entrenamiento:
                    raise UserError(_("Los empleados no deben tener campos de auditoría completados."))

    @api.depends('fecha_ultimo_entrenamiento', 'rol')
    def _needs_recertification(self):
        for record in self:
            if record.rol == 'auditor' and record.fecha_ultimo_entrenamiento:
                years_since_training = (fields.Date.today() - record.fecha_ultimo_entrenamiento).days / 365
                record.needs_recertification = years_since_training > 3
            else:
                record.needs_recertification = False

    needs_recertification = fields.Boolean(
        string='Necesita Recertificación',
        compute='_needs_recertification',
        store=True
    )

    def _check_recetification_alert(self):
        alerta_obj = self.env['electric.asset.management.alerta']
        for record in self:
            if record.needs_recertification:
                # Verificar si ya existe una alerta pendiente para evitar duplicados
                alerta_existente = alerta_obj.search([
                    ('responsable', '=', record.id),
                    ('categoria', '=', 'mantenimiento'),
                    ('estado', '=', 'pendiente'),
                    ('descripcion', 'ilike', 'recertificación')
                ], limit=1)

                if not alerta_existente:
                    alerta_obj.create({
                        'id_dispositivo': record.equipo_asignado.id if record.equipo_asignado else None,
                        'tipo_alerta': 'manual',
                        'descripcion': f"El auditor '{record.user_id.name}' necesita recertificación.",
                        'responsable': record.id,
                        'categoria': 'mantenimiento',
                        'impacto_energetico': 'medio',
                        'prioridad': 'media',
                        'contacto_responsable': record.user_id.id,
                    })
    @api.model
    def create(self, vals):
        record = super(Usuario, self).create(vals)
        record._check_recetification_alert()
        return record

    def write(self, vals):
        result = super(Usuario, self).write(vals)
        self._check_recetification_alert()
        return result
