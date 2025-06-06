from odoo import http
from odoo.http import request

class DashboardController(http.Controller):
    """
    controlador para manejar las solicitudes del dashboard.
    """

    @http.route('/electric_asset_management/dashboard', type='json', auth='user')
    def get_dashboard_data(self):
        """
        ruta principal para obtener todos los datos del dashboard.
        """
        # obtener los datos de cada modelo de los metodos en cada uno
        alerta_model = request.env['electric.asset.management.alerta']
        medicion_model = request.env['electric.asset.management.medicion']
        reporte_model = request.env['electric.asset.management.reporte']
        zona_model = request.env['electric.asset.management.zona']
        dispositivo_model = request.env['electric.asset.management.dispositivo']

        # llamar los metodos de cada modelo para proveer datos al dashboard
        alerta_data = alerta_model.data_alerta_dashboard()
        medicion_data = medicion_model.data_medicion_dashboard()
        reporte_data = reporte_model.data_reporte_dashboard()
        zona_data = zona_model.data_zona_dashboard()
        dispositivo_data = dispositivo_model.data_dispositivo_dashboard()

        # retorna los datos en formato json
        return {
            'alertas': alerta_data,
            'mediciones': medicion_data,
            'reportes': reporte_data,
            'zonas': zona_data,
            'dispositivos': dispositivo_data,
        }