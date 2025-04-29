/**@odoo-module */

import { registry } from "@web/core/registry";
import { KpiCard } from "./kpi_component/kpi_component";
import { ChartComponent } from "./chart_component/chart_component";
const { Component, onWillStart, useRef, onMounted, rpc } = owl;


export class ElectricDashboard extends Component {
    static template = "owl.OwlElectricDashboard";
    static components = { KpiCard, ChartComponent }

    constructor() {
        super(...arguments);
        this.data = null;
    }

    async GetDataDashboard () {
        try {   
        const data = await rpc('/electric_asset_management/dashboard', {
            metthod: 'GET',
        });
        
        this.data = data;
        console.log("Datos revogidos correctamente", data);
    } catch (error) {
        console.error("Error al traer los datos", error);
    }

        onMounted(() => {
            this.GetDataDashboard();
        })
    }
}

registry.category("actions").add("owl.electric_dashboard", ElectricDashboard);