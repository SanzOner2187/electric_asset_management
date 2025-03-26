# -*- coding: utf-8 -*-
# from odoo import http


# class ElectricAssetManagement(http.Controller):
#     @http.route('/electric_asset_management/electric_asset_management', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/electric_asset_management/electric_asset_management/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('electric_asset_management.listing', {
#             'root': '/electric_asset_management/electric_asset_management',
#             'objects': http.request.env['electric_asset_management.electric_asset_management'].search([]),
#         })

#     @http.route('/electric_asset_management/electric_asset_management/objects/<model("electric_asset_management.electric_asset_management"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('electric_asset_management.object', {
#             'object': obj
#         })


from odoo import http
from odoo.http import request

class ElectricAssetManagementController(http.Controller):
    @http.route('/electric_asset_management/dashboard', type='http', auth='user')
    def dashboard(self):
        return request.render('electric_asset_management.dashboard')

class ElectricDashboard(http.Controller):
    @http.route('/dashboard', auth='user', website=True)
    def dashboard(self, **kwargs):
        return http.request.render('electric_asset_management.dashboard_multi_graph')