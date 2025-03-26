odoo.define('electric_asset_management.dashboard', function (require) {
    "use strict";
    
    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var rpc = require('web.rpc');
    
    var EnergyDashboard = AbstractAction.extend({
        template: 'EnergyDashboard',
        events: {
            'click .o_menu_item': '_onMenuClick',
        },
    
        init: function(parent, action) {
            this._super.apply(this, arguments);
            this.dashboard_data = {};
        },
    
        willStart: function() {
            var self = this;
            return this._loadData().then(function() {
                return self._super.apply(self, arguments);
            });
        },
    
        start: function() {
            this._renderDashboard();
            return this._super.apply(this, arguments);
        },
    
        _loadData: function() {
            var self = this;
            return rpc.query({
                route: '/electric_asset_management/dashboard_data',
            }).then(function(data) {
                self.dashboard_data = data;
            });
        },
    
        _renderDashboard: function() {
            var self = this;
            this.$el.empty();
            
            // Renderizar el dashboard con los datos
            var $dashboard = $(`
                <div class="container-fluid">
                    <!-- Encabezado -->
                    <div class="row mb-4">
                        <div class="col-12 text-center">
                            <h1>Dashboard de Gestión Energética ISO 50001</h1>
                            <h4>${new Date().toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' })}</h4>
                        </div>
                    </div>
    
                    <!-- Primera fila: Resumen general -->
                    <div class="row mb-4">
                        <!-- Consumo total -->
                        <div class="col-md-4">
                            <div class="card border-primary">
                                <div class="card-header bg-primary text-white">
                                    <i class="fa fa-bolt mr-2"/> Consumo Total
                                </div>
                                <div class="card-body text-center">
                                    <h1>${self.dashboard_data.total_consumption} kWh</h1>
                                    <small class="text-muted">Este mes</small>
                                </div>
                            </div>
                        </div>
    
                        <!-- Costo total -->
                        <div class="col-md-4">
                            <div class="card border-success">
                                <div class="card-header bg-success text-white">
                                    <i class="fa fa-money mr-2"/> Costo Total
                                </div>
                                <div class="card-body text-center">
                                    <h1>$${self.dashboard_data.total_cost}</h1>
                                    <small class="text-muted">Este mes</small>
                                </div>
                            </div>
                        </div>
    
                        <!-- Eficiencia promedio -->
                        <div class="col-md-4">
                            <div class="card border-info">
                                <div class="card-header bg-info text-white">
                                    <i class="fa fa-line-chart mr-2"/> Eficiencia Promedio
                                </div>
                                <div class="card-body text-center">
                                    <h1>${self.dashboard_data.avg_efficiency}%</h1>
                                    <div class="progress mt-2">
                                        <div class="progress-bar ${self._getEfficiencyClass(self.dashboard_data.avg_efficiency)}" 
                                             style="width: ${self.dashboard_data.avg_efficiency}%;">
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
    
                    <!-- Segunda fila: Gráficos principales -->
                    <div class="row mb-4">
                        <!-- Consumo por zona -->
                        <div class="col-md-6">
                            <div class="card">
                                <div class="card-header">
                                    <i class="fa fa-map-marker mr-2"/> Consumo por Zona
                                </div>
                                <div class="card-body">
                                    <canvas id="zoneChart" style="height: 300px;"/>
                                </div>
                            </div>
                        </div>
    
                        <!-- Consumo por tipo de dispositivo -->
                        <div class="col-md-6">
                            <div class="card">
                                <div class="card-header">
                                    <i class="fa fa-pie-chart mr-2"/> Consumo por Tipo de Dispositivo
                                </div>
                                <div class="card-body">
                                    <canvas id="typeChart" style="height: 300px;"/>
                                </div>
                            </div>
                        </div>
                    </div>
    
                    <!-- Tercera fila: Alertas y dispositivos críticos -->
                    <div class="row mb-4">
                        <!-- Alertas recientes -->
                        <div class="col-md-6">
                            <div class="card border-danger">
                                <div class="card-header bg-danger text-white">
                                    <i class="fa fa-exclamation-triangle mr-2"/> Alertas Recientes
                                    <span class="badge badge-light float-right">${self.dashboard_data.alerts_count}</span>
                                </div>
                                <div class="card-body">
                                    <table class="table table-sm">
                                        <thead>
                                            <tr>
                                                <th>Dispositivo</th>
                                                <th>Tipo</th>
                                                <th>Fecha</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${self.dashboard_data.recent_alerts.map(alert => `
                                                <tr class="${alert.tipo_alerta === 'critica' ? 'table-danger' : 'table-warning'}">
                                                    <td>${alert.dispositivo}</td>
                                                    <td>${alert.tipo_alerta}</td>
                                                    <td>${alert.fecha}</td>
                                                </tr>
                                            `).join('')}
                                        </tbody>
                                    </table>
                                    <a href="#action=action_electric_asset_management_alerta" class="btn btn-sm btn-outline-danger float-right">Ver todas</a>
                                </div>
                            </div>
                        </div>
    
                        <!-- Dispositivos críticos -->
                        <div class="col-md-6">
                            <div class="card border-warning">
                                <div class="card-header bg-warning text-white">
                                    <i class="fa fa-warning mr-2"/> Dispositivos Críticos
                                </div>
                                <div class="card-body">
                                    <table class="table table-sm">
                                        <thead>
                                            <tr>
                                                <th>Dispositivo</th>
                                                <th>Consumo</th>
                                                <th>Eficiencia</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${self.dashboard_data.critical_devices.map(device => `
                                                <tr>
                                                    <td>${device.name}</td>
                                                    <td>${device.consumo} W</td>
                                                    <td>
                                                        <div class="progress" style="height: 20px;">
                                                            <div class="progress-bar ${self._getEfficiencyClass(device.eficiencia)}" 
                                                                 style="width: ${device.eficiencia}%;">
                                                                ${device.eficiencia}%
                                                            </div>
                                                        </div>
                                                    </td>
                                                </tr>
                                            `).join('')}
                                        </tbody>
                                    </table>
                                    <a href="#action=action_electric_asset_management_dispositivo" class="btn btn-sm btn-outline-warning float-right">Ver todos</a>
                                </div>
                            </div>
                        </div>
                    </div>
    
                    <!-- Cuarta fila: Reportes y objetivos -->
                    <div class="row">
                        <!-- Objetivos de reducción -->
                        <div class="col-md-6">
                            <div class="card border-info">
                                <div class="card-header bg-info text-white">
                                    <i class="fa fa-bullseye mr-2"/> Objetivos de Reducción
                                </div>
                                <div class="card-body">
                                    ${self.dashboard_data.zone_goals.map(goal => `
                                        <div class="mb-3">
                                            <h5>${goal.zona}</h5>
                                            <div class="d-flex justify-content-between mb-1">
                                                <span>Objetivo: ${goal.objetivo}%</span>
                                                <span>Actual: ${goal.actual}%</span>
                                            </div>
                                            <div class="progress" style="height: 20px;">
                                                <div class="progress-bar ${goal.actual >= goal.objetivo ? 'bg-success' : 'bg-danger'}" 
                                                     style="width: ${goal.actual > goal.objetivo ? 100 : (goal.actual / goal.objetivo * 100)}%;">
                                                    ${goal.actual > goal.objetivo ? 'Meta superada' : (goal.actual / goal.objetivo * 100).toFixed(1) + '%'}
                                                </div>
                                            </div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        </div>
    
                        <!-- Últimos reportes -->
                        <div class="col-md-6">
                            <div class="card">
                                <div class="card-header">
                                    <i class="fa fa-file-text mr-2"/> Últimos Reportes
                                </div>
                                <div class="card-body">
                                    ${self.dashboard_data.recent_reports.map(report => `
                                        <div class="mb-3 border-bottom pb-2">
                                            <div class="d-flex justify-content-between">
                                                <strong>${report.name}</strong>
                                                <span class="badge ${report.estado === 'generado' ? 'badge-success' : report.estado === 'enviado' ? 'badge-primary' : 'badge-secondary'}">
                                                    ${report.estado}
                                                </span>
                                            </div>
                                            <div class="text-muted small">${report.fecha}</div>
                                            <div class="mt-1">${report.descripcion}</div>
                                        </div>
                                    `).join('')}
                                    <a href="#action=action_electric_asset_management_reporte" class="btn btn-sm btn-outline-primary float-right">Ver todos</a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `);
    
            this.$el.append($dashboard);
            
            // Inicializar gráficos
            this._initCharts();
        },
    
        _getEfficiencyClass: function(efficiency) {
            if (efficiency < 70) return 'bg-danger';
            if (efficiency < 85) return 'bg-warning';
            return 'bg-success';
        },
    
        _initCharts: function() {
            // Gráfico de barras - Consumo por zona
            var zoneCtx = document.getElementById('zoneChart').getContext('2d');
            new Chart(zoneCtx, {
                type: 'bar',
                data: {
                    labels: this.dashboard_data.consumption_by_zone.labels,
                    datasets: [{
                        label: 'Consumo (kWh)',
                        data: this.dashboard_data.consumption_by_zone.data,
                        backgroundColor: 'rgba(54, 162, 235, 0.7)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
    
            // Gráfico de pie - Consumo por tipo
            var typeCtx = document.getElementById('typeChart').getContext('2d');
            new Chart(typeCtx, {
                type: 'pie',
                data: {
                    labels: this.dashboard_data.consumption_by_type.labels,
                    datasets: [{
                        data: this.dashboard_data.consumption_by_type.data,
                        backgroundColor: [
                            'rgba(255, 99, 132, 0.7)',
                            'rgba(54, 162, 235, 0.7)',
                            'rgba(255, 206, 86, 0.7)',
                            'rgba(75, 192, 192, 0.7)',
                            'rgba(153, 102, 255, 0.7)',
                            'rgba(255, 159, 64, 0.7)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true
                }
            });
        },
    
        _onMenuClick: function(ev) {
            ev.preventDefault();
            var actionId = $(ev.currentTarget).attr('data-menu');
            if (actionId) {
                this.do_action(actionId);
            }
        }
    });
    
    core.action_registry.add('electric_asset_management.dashboard', EnergyDashboard);
    
    return EnergyDashboard;
    });