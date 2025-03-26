# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class EnergyDashboard(http.Controller):
    @http.route('/electric_asset_management/dashboard_data', type='json', auth='user')
    def dashboard_data(self):
        env = request.env
        today = datetime.now()
        start_of_month = today.replace(day=1)
        end_of_month = (start_of_month + relativedelta(months=1)) - timedelta(days=1)

        # Consumo total
        consumo_mensual = sum(env['electric.asset.management.dispositivo'].search([]).mapped('consumo_mensual_kwh'))
        costo_mensual = sum(env['electric.asset.management.dispositivo'].search([]).mapped('costo_mensual'))

        # Eficiencia promedio
        dispositivos = env['electric.asset.management.dispositivo'].search([('eficiencia_operativa', '>', 0)])
        eficiencia_promedio = sum(dispositivos.mapped('eficiencia_operativa')) / len(dispositivos) if dispositivos else 0

        # Consumo por zona
        zonas = env['electric.asset.management.zona'].search([])
        consumo_por_zona = {
            'labels': [z.name for z in zonas],
            'data': [sum(z.dispositivo_ids.mapped('consumo_mensual_kwh')) for z in zonas]
        }

        # Consumo por tipo
        tipos = env['electric.asset.management.dispositivo'].read_group([], ['tipo', 'consumo_mensual_kwh:sum'], ['tipo'])
        consumo_por_tipo = {
            'labels': [t['tipo'] or 'Sin tipo' for t in tipos],
            'data': [t['consumo_mensual_kwh'] for t in tipos]
        }

        # Alertas recientes
        alertas = env['electric.asset.management.alerta'].search([], limit=5, order='fecha_hora desc')
        alertas_data = [{
            'dispositivo': a.id_dispositivo.name,
            'tipo_alerta': a.tipo_alerta,
            'fecha': a.fecha_hora.strftime('%d/%m/%Y %H:%M')
        } for a in alertas]

        # Dispositivos críticos
        dispositivos_criticos = env['electric.asset.management.dispositivo'].search(
            [('es_equipo_critico', '=', True)], 
            order='consumo_energetico desc', 
            limit=5
        )
        dispositivos_data = [{
            'name': d.name,
            'consumo': d.consumo_energetico,
            'eficiencia': d.eficiencia_operativa
        } for d in dispositivos_criticos]

        # Objetivos por zona
        objetivos_data = [{
            'zona': z.name,
            'objetivo': z.objetivo_reduccion,
            'actual': 100 * (1 - (sum(z.dispositivo_ids.mapped('consumo_mensual_kwh')) / z.consumo_referencia)) if z.consumo_referencia > 0 else 0
        } for z in zonas if z.objetivo_reduccion > 0]

        # Últimos reportes
        reportes = env['electric.asset.management.reporte'].search([], limit=3, order='fecha_generacion desc')
        reportes_data = [{
            'name': r.tipo_reporte.upper(),
            'fecha': r.fecha_generacion.strftime('%d/%m/%Y'),
            'estado': r.estado,
            'descripcion': f"Consumo: {r.consumo_total} kWh - Eficiencia: {r.eficiencia_energetica}%"
        } for r in reportes]

        return {
            "total_consumption": round(consumo_mensual, 2),
            "total_cost": round(costo_mensual, 2),
            "avg_efficiency": round(eficiencia_promedio, 1),
            "consumption_by_zone": consumo_por_zona,
            "consumption_by_type": consumo_por_tipo,
            "alerts_count": env['electric.asset.management.alerta'].search_count([('estado', '=', 'pendiente')]),
            "recent_alerts": alertas_data,
            "critical_devices": dispositivos_data,
            "zone_goals": objetivos_data,
            "recent_reports": reportes_data
        }