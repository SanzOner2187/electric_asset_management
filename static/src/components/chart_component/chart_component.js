/**@odoo-module */

import { registry } from "@web/core/registry";
const { Component, onWillStart, useRef, onMounted } = owl;


export class ChartComponent extends Component {
    setup(){
        this.chartRef = useRef("chart")

        onMounted(() =>this.ComponentChart())
    }

    ComponentChart () {
        new Chart(this.chartRef.el,
            {
              type: this.props.type,
              data: {
                labels: [
                    'Red',
                    'Blue',
                    'Yellow',
                ],
                datasets: [
                    {
                    label: 'primer grafico',
                    data: [300, 50, 100],
                    hoverOffset: 4
                }, {
                    label: 'segundo grafico',
                    data: [100, 70, 150],
                    hoverOffset: 4
                }]
              },
              options: {
                reponsive: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                    },
                    title: {
                        display: true,
                        title: this.props.title,
                    }
                }
              }
            }
          );
    }
}

ChartComponent.template = "owl.ChartComponent";