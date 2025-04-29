/**@odoo-module */

const { Component } = owl;

export class KpiCard extends Component {
    constructor() {
        super(...arguments);
        console.log("Kpis renderizados correctamente");
    }
}

KpiCard.template = "owl.KpiComponent"