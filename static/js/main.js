document.addEventListener('DOMContentLoaded', function() {
    const macroChartCanvas = document.getElementById('macroChart');
    
    if (macroChartCanvas) {
        const recommendations = JSON.parse(macroChartCanvas.dataset.recommendations || '{}');
        
        new Chart(macroChartCanvas, {
            type: 'doughnut',
            data: {
                labels: ['Protein', 'Carbohydrates', 'Fat'],
                datasets: [{
                    data: [
                        recommendations.protein,
                        recommendations.carbs,
                        recommendations.fat
                    ],
                    backgroundColor: [
                        '#0d6efd',  
                        '#198754',  
                        '#ffc107'   
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
    
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    }
    
    const veganCheckbox = document.getElementById('vegan');
    const vegetarianCheckbox = document.getElementById('vegetarian');
    
    if (veganCheckbox && vegetarianCheckbox) {
        veganCheckbox.addEventListener('change', function() {
            if (this.checked) {
                vegetarianCheckbox.checked = true;
                vegetarianCheckbox.disabled = true;
            } else {
                vegetarianCheckbox.disabled = false;
            }
        });
    }
});
