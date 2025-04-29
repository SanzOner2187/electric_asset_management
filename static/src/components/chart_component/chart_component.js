/**@odoo-module */

import { registry } from "@web/core/registry";
const { Component, onWillStart, useRef, onMounted, rpc } = owl;


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
                    'orange',
                    'green',
                    'purple',
                ],
                datasets: [
                    {
                    label: 'primer grafico',
                    data: [300, 79, 100, 200, 350, 400],
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

          console.log("Graficos renderizados correctamente")
    }
}

ChartComponent.template = "owl.ChartComponent";