from odoo import models, fields, api, _
from odoo.exceptions import UserError

class Usuario(models.Model):
    _name = 'electric.asset.management.usuario'
    _description = 'Usuarios del sistema'
    _inherits = {'res.users': 'user_id'}
    
    user_id = fields.Many2one('res.users', string='Nombre', required=True, ondelete='cascade')
    login = fields.Char(related='user_id.login', string='Correo', store=True, readonly=False)
    rol = fields.Char(string='Rol')
    password = fields.Char(string='Contraseña', password=True)
    fecha_registro = fields.Datetime(string='Fecha de Registro', default=fields.Datetime.now)
    
    es_auditor_energia = fields.Boolean(string='Auditor de Energía')
    certificaciones = fields.Text(string='Certificaciones Energéticas')
    fecha_ultimo_entrenamiento = fields.Date(string='Último Entrenamiento')
    area_responsable = fields.Many2one('electric.asset.management.zona', string='Área Responsable')