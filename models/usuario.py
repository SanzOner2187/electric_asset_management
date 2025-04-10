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
    certificaciones = fields.Text(string='Certificaciones Energéticas', help="Certificaciones relevantes para la gestión energética.")
    fecha_ultimo_entrenamiento = fields.Date(string='Último Entrenamiento', help="Fecha del último entrenamiento en gestión energética.")

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

    # Método para verificar si el usuario necesita recertificación (solo para auditores)
    def _needs_recertification(self):
        """Verifica si el usuario necesita recertificación basada en la fecha del último entrenamiento."""
        for record in self:
            if record.rol == 'auditor' and record.fecha_ultimo_entrenamiento:
                years_since_training = (fields.Date.today() - record.fecha_ultimo_entrenamiento).days / 365
                record.needs_recertification = years_since_training > 3  # Ejemplo: recertificación cada 3 años
            else:
                record.needs_recertification = False

    needs_recertification = fields.Boolean(string='Necesita Recertificación', compute='_needs_recertification', store=True)