/**@odoo-module */

import { registry } from "@web/core/registry";
import { KpiCard } from "./kpi_component/kpi_component";
import { ChartComponent } from "./chart_component/chart_component";
const { Component, onWillStart, useRef, onMounted } = owl;


export class ElectricDashboard extends Component {
    setup(){
        
    }
}

ElectricDashboard.template = "owl.OwlElectricDashboard";
ElectricDashboard.components= { KpiCard, ChartComponent}

registry.category("actions").add("owl.electric_dashboard", ElectricDashboard);